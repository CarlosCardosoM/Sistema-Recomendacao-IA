from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json

from database import Aluno, Sessao, Mensagem, ChunkUsage, Conteudo
from controllers.aluno_controller import buscar_aluno_por_email
from services.rag_service import processar_pergunta
from services.ollama_service import gerar_resposta, analisar_pergunta
from services.embedding_service import bytes_para_embedding
from services.recomendacao_service import recomendar_conteudo


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


def encerrar_sessao(db: Session, sessao_id: int) -> dict:
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    sessao.data_hora_fim = datetime.now()
    db.commit()
    return {"mensagem": "Sessão encerrada com sucesso."}


def excluir_sessao(db: Session, sessao_id: int) -> dict:
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    mensagens = db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).all()
    for mensagem in mensagens:
        db.query(ChunkUsage).filter(ChunkUsage.mensagem_id == mensagem.id).delete()
    db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).delete()
    db.delete(sessao)
    db.commit()
    return {"mensagem": "Sessão excluída com sucesso."}


def responder_pergunta(db: Session, sessao_id: int, pergunta: str) -> dict:
    """
    Pipeline completo do chat:
    1. Busca histórico da sessão
    2. Processa RAG — classificação da pergunta define o threshold
    3. Gera resposta + análise em paralelo
    4. Salva mensagens no banco
    5. Só gera recomendações se RAG encontrou conteúdos relevantes
       → pergunta genérica = sem conteúdos = sem recomendações
    """
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    aluno = db.query(Aluno).filter(Aluno.id == sessao.aluno_id).first()

    # 1. Busca histórico
    historico_banco = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    # 2. Processa RAG
    # classificar_pergunta() roda dentro de buscar_conteudos_relevantes()
    # e define o threshold antes de buscar — resultado correto garantido
    resultado_rag = processar_pergunta(db, pergunta, historico_banco)

    # 3. Gera resposta e análise em paralelo
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

    # 4. Salva a pergunta do aluno
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

    # 5. Salva a resposta do assistente
    mensagem_assistente = Mensagem(
        sessao_id          = sessao_id,
        papel              = "assistente",
        conteudo           = resposta,
        analise_pergunta   = None,
        embedding_pergunta = None
    )
    db.add(mensagem_assistente)
    db.commit()

    # 6. Registra ChunkUsage apenas se encontrou conteúdos relevantes
    conteudos_relevantes = resultado_rag["conteudos_relevantes"]
    for conteudo, score in conteudos_relevantes:
        chunk = ChunkUsage(
            mensagem_id        = mensagem_aluno.id,
            conteudo_id        = conteudo.id,
            similaridade_score = score
        )
        db.add(chunk)
    db.commit()

    # 7. Só gera recomendações se o RAG encontrou conteúdos relevantes
    # Se conteudos_relevantes estiver vazio, a pergunta foi classificada
    # como genérica/saudação — não recomenda nada
    if not conteudos_relevantes:
        recomendacoes = []
    else:
        embedding_pergunta = bytes_para_embedding(resultado_rag["embedding_pergunta"])
        recomendacoes = recomendar_conteudo(
            db                 = db,
            email              = aluno.email,
            embedding_pergunta = embedding_pergunta,
            nivel_pergunta     = analise.get("nivel_dificuldade")
        )

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


def buscar_historico(db: Session, sessao_id: int) -> list:
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    mensagens = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    resultado = []
    for m in mensagens:
        mensagem_dict = {
            "papel":     m.papel,
            "conteudo":  m.conteudo,
            "criado_em": str(m.criado_em),
        }

        if m.papel == "usuario":
            chunks = db.query(ChunkUsage).filter(
                ChunkUsage.mensagem_id == m.id
            ).all()
            if chunks:
                recomendacoes = []
                for chunk in chunks:
                    conteudo = db.query(Conteudo).filter(
                        Conteudo.id == chunk.conteudo_id
                    ).first()
                    if conteudo:
                        recomendacoes.append({
                            "conteudo_id": conteudo.id,
                            "titulo":      conteudo.titulo,
                            "tipo":        conteudo.tipo,
                            "link":        conteudo.link,
                            "score":       round(chunk.similaridade_score, 3)
                        })
                mensagem_dict["recomendacoes"] = recomendacoes

        resultado.append(mensagem_dict)

    # Passa recomendações para a mensagem do assistente seguinte
    historico_agrupado = []
    for i, msg in enumerate(resultado):
        if msg["papel"] == "usuario" and "recomendacoes" in msg:
            recomendacoes = msg.pop("recomendacoes")
            historico_agrupado.append(msg)
            if i + 1 < len(resultado) and resultado[i + 1]["papel"] == "assistente":
                resultado[i + 1]["recomendacoes"] = recomendacoes
        else:
            historico_agrupado.append(msg)

    return historico_agrupado