from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from controllers.chat_controller import (
    iniciar_sessao,
    encerrar_sessao,
    excluir_sessao,
    responder_pergunta,
    buscar_historico
)

router = APIRouter(prefix="/chat", tags=["Chat"])


class IniciarSessaoRequest(BaseModel):
    email: str

class PerguntaRequest(BaseModel):
    pergunta: str


@router.post("/sessao")
def criar_sessao(dados: IniciarSessaoRequest, db: Session = Depends(get_db)):
    sessao = iniciar_sessao(db, dados.email)
    return {
        "sessao_id":        sessao.id,
        "mensagem":         "Sessão iniciada com sucesso.",
        "data_hora_inicio": sessao.data_hora_inicio
    }


@router.delete("/sessao/{sessao_id}/encerrar")
def fechar_sessao(sessao_id: int, db: Session = Depends(get_db)):
    """Encerra a sessão preenchendo data_hora_fim (mantém no banco)."""
    return encerrar_sessao(db, sessao_id)


@router.delete("/sessao/{sessao_id}")
def deletar_sessao(sessao_id: int, db: Session = Depends(get_db)):
    """Exclui a sessão e todos os dados vinculados (mensagens e chunks)."""
    return excluir_sessao(db, sessao_id)


@router.post("/sessao/{sessao_id}/perguntar")
def perguntar(sessao_id: int, dados: PerguntaRequest, db: Session = Depends(get_db)):
    return responder_pergunta(db, sessao_id, dados.pergunta)


@router.get("/sessao/{sessao_id}/historico")
def historico(sessao_id: int, db: Session = Depends(get_db)):
    return buscar_historico(db, sessao_id)