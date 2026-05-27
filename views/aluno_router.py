from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.aluno_schema import (
    AlunoCriar,
    AlunoResposta,
    AlunoAtualizarEmail,
    AlunoAtualizarSenha,
    AlunoAtualizarPreferencias
)
from controllers.aluno_controller import (
    criar_aluno,
    buscar_aluno_por_email,
    atualizar_email,
    atualizar_senha,
    atualizar_preferencias
)

router = APIRouter(prefix="/alunos", tags=["Alunos"])


@router.post("/", response_model=AlunoResposta)
def cadastrar_aluno(dados: AlunoCriar, db: Session = Depends(get_db)):
    return criar_aluno(db, dados)


@router.get("/{email}", response_model=AlunoResposta)
def buscar_aluno(email: str, db: Session = Depends(get_db)):
    return buscar_aluno_por_email(db, email)


@router.put("/{email}/email", response_model=AlunoResposta)
def editar_email(email: str, dados: AlunoAtualizarEmail, db: Session = Depends(get_db)):
    return atualizar_email(db, email, dados.novo_email)


@router.put("/{email}/senha")
def editar_senha(email: str, dados: AlunoAtualizarSenha, db: Session = Depends(get_db)):
    atualizar_senha(db, email, dados.senha_atual, dados.nova_senha)
    return {"mensagem": "Senha atualizada com sucesso."}


@router.put("/{email}/preferencias", response_model=AlunoResposta)
def editar_preferencias(email: str, dados: AlunoAtualizarPreferencias, db: Session = Depends(get_db)):
    return atualizar_preferencias(db, email, dados.preferencias_tipos)