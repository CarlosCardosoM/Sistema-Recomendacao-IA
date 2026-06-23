from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from controllers.interacao_controller import (
    abrir_conteudo,
    fechar_conteudo,
    listar_interacoes_aluno,
    contar_conteudos_abertos
)

router = APIRouter(prefix="/interacoes", tags=["Interações"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AbrirConteudoRequest(BaseModel):
    email: str
    conteudo_id: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/abrir")
def abrir(dados: AbrirConteudoRequest, db: Session = Depends(get_db)):
    """Registra que o aluno abriu um conteúdo."""
    interacao = abrir_conteudo(db, dados.email, dados.conteudo_id)
    return {
        "interacao_id": interacao.id,
        "mensagem":     "Conteúdo aberto com sucesso.",
        "aberto_em":    interacao.aberto_em
    }


@router.put("/{interacao_id}/fechar")
def fechar(interacao_id: int, db: Session = Depends(get_db)):
    """Registra o fechamento do conteúdo e calcula o tempo de visualização."""
    interacao = fechar_conteudo(db, interacao_id)
    return {
        "mensagem":            "Conteúdo fechado com sucesso.",
        "tempo_visualizacao":  interacao.tempo_visualizacao
    }


@router.get("/{email}")
def listar(email: str, db: Session = Depends(get_db)):
    """Lista o histórico de interações do aluno."""
    return listar_interacoes_aluno(db, email)


@router.get("/{email}/contagem")
def contagem(email: str, db: Session = Depends(get_db)):
    """Retorna quantos conteúdos o aluno já abriu."""
    total = contar_conteudos_abertos(db, email)
    return {"quantidade_conteudos_abertos": total}