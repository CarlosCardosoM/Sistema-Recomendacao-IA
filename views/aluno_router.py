from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.aluno_schema import AlunoCriar, AlunoResposta
from controllers.aluno_controller import criar_aluno, buscar_aluno_por_email

router = APIRouter(prefix="/alunos", tags=["Alunos"])


@router.post("/", response_model=AlunoResposta)
def cadastrar_aluno(dados: AlunoCriar, db: Session = Depends(get_db)):
    return criar_aluno(db, dados)


@router.get("/{email}", response_model=AlunoResposta)
def buscar_aluno(email: str, db: Session = Depends(get_db)):
    return buscar_aluno_por_email(db, email)