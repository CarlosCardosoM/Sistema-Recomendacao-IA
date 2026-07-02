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
    """
    Exclui a sessão e todos os dados vinculados:
    ChunkUsage → Mensagem → Sessao (nessa ordem por causa das FKs)
    """
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    # 1. Remove ChunkUsage vinculados às mensagens desta sessão
    mensagens = db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).all()
    for mensagem in mensagens:
        db.query(ChunkUsage).filter(ChunkUsage.mensagem_id == mensagem.id).delete()

    # 2. Remove as mensagens
    db.query(Mensagem).filter(Mensagem.sessao_id == sessao_id).delete()

    # 3. Remove a sessão
    db.delete(sessao)
    db.commit()

    return {"mensagem": "Sessão excluída com sucesso."}


def responder_pergunta(db: Session, sessao_id: int, pergunta: str) -> dict:
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    aluno = db.query(Aluno).filter(Aluno.id == sessao.aluno_id).first()

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

    mensagem_assistente = Mensagem(
        sessao_id          = sessao_id,
        papel              = "assistente",
        conteudo           = resposta,
        analise_pergunta   = None,
        embedding_pergunta = None
    )
    db.add(mensagem_assistente)
    db.commit()

    for conteudo, score in resultado_rag["conteudos_relevantes"]:
        chunk = ChunkUsage(
            mensagem_id        = mensagem_aluno.id,
            conteudo_id        = conteudo.id,
            similaridade_score = score
        )
        db.add(chunk)
    db.commit()

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
            {"titulo": c.titulo, "link": c.link, "similaridade": round(score, 2)}
            for c, score in resultado_rag["conteudos_relevantes"]
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
            chunks = db.query(ChunkUsage).filter(ChunkUsage.mensagem_id == m.id).all()
            if chunks:
                recomendacoes = []
                for chunk in chunks:
                    conteudo = db.query(Conteudo).filter(Conteudo.id == chunk.conteudo_id).first()
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

    # Agrupa recomendações na mensagem do assistente que segue o usuário
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