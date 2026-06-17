from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from database import Aluno, Sessao, Mensagem, ChunkUsage
from controllers.aluno_controller import buscar_aluno_por_email
from services.rag_service import processar_pergunta
from services.ollama_service import gerar_resposta


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


def responder_pergunta(db: Session, sessao_id: int, pergunta: str) -> dict:
    """
    Pipeline completo do chat:
    1. Busca o histórico da sessão
    2. Processa a pergunta com o RAG
    3. Gera a resposta com o Ollama
    4. Salva a pergunta e a resposta no banco
    5. Registra os conteúdos usados pelo RAG

    Segue a função responderPergunta() do pseudocódigo.
    """
    # Verifica se a sessão existe
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    # 1. Busca o histórico de mensagens da sessão
    historico_banco = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    # 2. Processa a pergunta com o RAG
    resultado_rag = processar_pergunta(db, pergunta, historico_banco)

    # 3. Gera a resposta com o Ollama
    resposta = gerar_resposta(
        pergunta  = pergunta,
        contexto  = resultado_rag["contexto"],
        historico = resultado_rag["historico"]
    )

    # 4. Salva a pergunta do aluno no banco
    mensagem_aluno = Mensagem(
        sessao_id          = sessao_id,
        papel              = "usuario",
        conteudo           = pergunta,
        analise_pergunta   = None,
        embedding_pergunta = resultado_rag["embedding_pergunta"]
    )
    db.add(mensagem_aluno)
    db.commit()
    db.refresh(mensagem_aluno)

    # 5. Salva a resposta do assistente no banco
    mensagem_assistente = Mensagem(
        sessao_id          = sessao_id,
        papel              = "assistente",
        conteudo           = resposta,
        analise_pergunta   = None,
        embedding_pergunta = None
    )
    db.add(mensagem_assistente)
    db.commit()

    # 6. Registra os conteúdos usados pelo RAG na ChunkUsage
    for conteudo, score in resultado_rag["conteudos_relevantes"]:
        chunk = ChunkUsage(
            mensagem_id        = mensagem_aluno.id,
            conteudo_id        = conteudo.id,
            similaridade_score = score
        )
        db.add(chunk)
    db.commit()

    return {
        "resposta":            resposta,
        "conteudos_relevantes": [
            {
                "titulo":     c.titulo,
                "link":       c.link,
                "similaridade": round(score, 2)
            }
            for c, score in resultado_rag["conteudos_relevantes"]
        ]
    }


def buscar_historico(db: Session, sessao_id: int) -> list:
    """
    Retorna o histórico de mensagens de uma sessão.
    """
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    mensagens = db.query(Mensagem).filter(
        Mensagem.sessao_id == sessao_id
    ).order_by(Mensagem.criado_em).all()

    return [
        {
            "papel":     m.papel,
            "conteudo":  m.conteudo,
            "criado_em": m.criado_em
        }
        for m in mensagens
    ]