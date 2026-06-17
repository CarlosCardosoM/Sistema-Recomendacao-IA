from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from controllers.chat_controller import (
    iniciar_sessao,
    encerrar_sessao,
    responder_pergunta,
    buscar_historico
)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class IniciarSessaoRequest(BaseModel):
    email: str

class PerguntaRequest(BaseModel):
    pergunta: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessao")
def criar_sessao(dados: IniciarSessaoRequest, db: Session = Depends(get_db)):
    """Inicia uma nova sessão de chat para o aluno."""
    sessao = iniciar_sessao(db, dados.email)
    return {
        "sessao_id":       sessao.id,
        "mensagem":        "Sessão iniciada com sucesso.",
        "data_hora_inicio": sessao.data_hora_inicio
    }


@router.delete("/sessao/{sessao_id}")
def fechar_sessao(sessao_id: int, db: Session = Depends(get_db)):
    """Encerra a sessão de chat."""
    return encerrar_sessao(db, sessao_id)


@router.post("/sessao/{sessao_id}/perguntar")
def perguntar(sessao_id: int, dados: PerguntaRequest, db: Session = Depends(get_db)):
    """
    Recebe a pergunta do aluno e retorna a resposta do EduBot
    junto com os conteúdos relevantes encontrados pelo RAG.
    """
    return responder_pergunta(db, sessao_id, dados.pergunta)


@router.get("/sessao/{sessao_id}/historico")
def historico(sessao_id: int, db: Session = Depends(get_db)):
    """Retorna o histórico de mensagens de uma sessão."""
    return buscar_historico(db, sessao_id)