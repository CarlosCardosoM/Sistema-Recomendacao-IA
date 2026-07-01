from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import json

from database import Aluno, Sessao, Mensagem, ChunkUsage
from controllers.aluno_controller import buscar_aluno_por_email
from services.rag_service import processar_pergunta
from services.ollama_service import gerar_resposta, analisar_pergunta
from services.embedding_service import bytes_para_embedding
from services.recomendacao_service import recomendar_conteudo


def iniciar_sessao(db: Session, email: str) -> Sessao:
    """
    Cria uma nova sessão de chat para o aluno.
    Chamado quando o aluno faz login e começa a conversar.
    """
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
    """
    Encerra a sessão de chat preenchendo data_hora_fim.
    """
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
    3.1 Analisa a pergunta (tópico, subtópicos, nível de dificuldade)
    4. Salva a pergunta e a resposta no banco
    5. Registra os conteúdos usados pelo RAG
    6. Gera recomendações personalizadas de conteúdo

    Segue as funções responderPergunta() e recomendarConteudo() do pseudocódigo.
    """
    # Verifica se a sessão existe
    sessao = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    # Busca o aluno dono da sessão — necessário para a recomendação
    aluno = db.query(Aluno).filter(Aluno.id == sessao.aluno_id).first()

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

    # 3.1 Analisa a pergunta para extrair tópico, subtópicos e nível de dificuldade
    analise = analisar_pergunta(pergunta)
    print("ANÁLISE DA PERGUNTA:", analise)  # debug temporário

    # 4. Salva a pergunta do aluno no banco
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

    # 7. Gera recomendações personalizadas combinando similaridade,
    #    preferências, curtidas, histórico e dificuldade
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
            for c, score in resultado_rag["conteudos_relevantes"]
        ],
        "recomendacoes": recomendacoes
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