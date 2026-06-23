from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from controllers.curtida_controller import (
    curtir_conteudo,
    remover_curtida,
    listar_curtidas_aluno,
    verificar_curtida
)

router = APIRouter(prefix="/curtidas", tags=["Curtidas"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CurtidaRequest(BaseModel):
    email: str
    conteudo_id: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/")
def curtir(dados: CurtidaRequest, db: Session = Depends(get_db)):
    """Registra a curtida de um aluno em um conteúdo."""
    return curtir_conteudo(db, dados.email, dados.conteudo_id)


@router.delete("/")
def descurtir(dados: CurtidaRequest, db: Session = Depends(get_db)):
    """Remove a curtida de um aluno em um conteúdo."""
    return remover_curtida(db, dados.email, dados.conteudo_id)


@router.get("/{email}")
def listar(email: str, db: Session = Depends(get_db)):
    """Lista todos os conteúdos curtidos pelo aluno."""
    return listar_curtidas_aluno(db, email)


@router.get("/{email}/{conteudo_id}/verificar")
def verificar(email: str, conteudo_id: int, db: Session = Depends(get_db)):
    """Verifica se o aluno curtiu um conteúdo específico."""
    curtiu = verificar_curtida(db, email, conteudo_id)
    return {"curtiu": curtiu}