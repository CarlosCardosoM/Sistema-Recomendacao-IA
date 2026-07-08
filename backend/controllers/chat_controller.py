from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json

from database import Aluno, Sessao, Mensagem, ChunkUsage, Conteudo
from controllers.aluno_controller import buscar_aluno_por_email
from services.rag_service import processar_pergunta
from services.ollama_service import gerar_resposta, analisar_pergunta
from services.recomendacao_service import recomendar_conteudo


def _buscar_sessao_do_aluno(db: Session, sessao_id: int, email: str) -> Sessao:
   
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    aluno = buscar_aluno_por_email(db, email)
    if sessao.aluno_id != aluno.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar esta sessão.")

    return sessao


def iniciar_sessao(db: Session, email: str) -> Sessao:
    aluno = buscar_aluno_por_email(db, email)
    sessao = Sessao(
        aluno_id         = aluno.id,
        data_hora_inicio = datetime.now()
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return sessao


def encerrar_sessao(db: Session, sessao_id: int, email: str) -> dict:
    sessao = _buscar_sessao_do_aluno(db, sessao_id, email)
    sessao.data_hora_fim = datetime.now()
    db.commit()
    return {"mensagem": "Sessão encerrada com sucesso."}


def excluir_sessao(db: Session, sessao_id: int, email: str) -> dict:
    sessao = _buscar_sessao_do_aluno(db, sessao_id, email)
    mensagens = db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).all()
    for mensagem in mensagens:
        db.query(ChunkUsage).filter(ChunkUsage.mensagem_id == mensagem.id).delete()
    db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).delete()
    db.delete(sessao)
    db.commit()
    return {"mensagem": "Sessão excluída com sucesso."}


def responder_pergunta(db: Session, sessao_id: int, pergunta: str, email: str) -> dict:
    sessao = _buscar_sessao_do_aluno(db, sessao_id, email)
    aluno  = db.query(Aluno).filter(Aluno.id == sessao.aluno_id).first()

    historico_banco = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    resultado_rag = processar_pergunta(db, pergunta, historico_banco)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_resposta = executor.submit(
            gerar_resposta,
            pergunta  = pergunta,
            contexto  = resultado_rag["contexto"],
            historico = resultado_rag["historico"]
        )
        futuro_analise = executor.submit(analisar_pergunta, pergunta)
        resposta = futuro_resposta.result()
        analise  = futuro_analise.result()

    # Salva pergunta do aluno
    mensagem_aluno = Mensagem(
        sessao_id          = sessao_id,
        papel              = "usuario",
        conteudo           = pergunta,
        analise_pergunta   = json.dumps(analise, ensure_ascii=False),
        embedding_pergunta = resultado_rag["embedding_pergunta"]
    )
    db.add(mensagem_aluno)
    db.commit()
    db.refresh(mensagem_aluno)

    # Registra ChunkUsage
    conteudos_relevantes = resultado_rag["conteudos_relevantes"]
    for conteudo, score in conteudos_relevantes:
        chunk = ChunkUsage(
            mensagem_id        = mensagem_aluno.id,
            conteudo_id        = conteudo.id,
            similaridade_score = score
        )
        db.add(chunk)
    db.commit()

    # Gera recomendações personalizadas — usa o pool amplo de candidatos
    # (não só os 3 do contexto do LLM), pra preferência de tipo do aluno ter
    # opções de sobra pra escolher dentro do que já é relevante pra pergunta
    candidatos_recomendacao = resultado_rag["candidatos_recomendacao"]
    if not candidatos_recomendacao:
        recomendacoes = []
    else:
        recomendacoes = recomendar_conteudo(
            db                   = db,
            email                = aluno.email,
            conteudos_relevantes = candidatos_recomendacao,
            nivel_pergunta       = analise.get("nivel_dificuldade")
        )

    # Salva resposta do assistente
    # Guarda as recomendações no campo analise_pergunta da mensagem do assistente
    # para recuperar corretamente no histórico sem perder dados
    mensagem_assistente = Mensagem(
        sessao_id          = sessao_id,
        papel              = "assistente",
        conteudo           = resposta,
        analise_pergunta   = json.dumps(recomendacoes, ensure_ascii=False),
        embedding_pergunta = None
    )
    db.add(mensagem_assistente)
    db.commit()

    return {
        "resposta":             resposta,
        "analise_pergunta":     analise,
        "conteudos_relevantes": [
            {
                "titulo":       c.titulo,
                "link":         c.link,
                "similaridade": round(score, 2)
            }
            for c, score in conteudos_relevantes
        ],
        "recomendacoes": recomendacoes
    }


def buscar_historico(db: Session, sessao_id: int, email: str) -> list:
    _buscar_sessao_do_aluno(db, sessao_id, email)

    mensagens = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    historico = []
    for m in mensagens:
        mensagem_dict = {
            "papel":    m.papel,
            "conteudo": m.conteudo,
        }

        if m.papel == "assistente" and m.analise_pergunta:
            # Recomendações ficam salvas no analise_pergunta da mensagem do assistente
            try:
                recomendacoes = json.loads(m.analise_pergunta)
                if isinstance(recomendacoes, list):
                    mensagem_dict["recomendacoes"] = recomendacoes
            except Exception:
                mensagem_dict["recomendacoes"] = []

        historico.append(mensagem_dict)

    return historico