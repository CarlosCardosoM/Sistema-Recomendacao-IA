from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.aluno_schema import (
    AlunoCriar,
    AlunoResposta,
    AlunoAtualizarEmail,
    AlunoAtualizarPreferencias,
    AlunoVerificarToken,
    AlunoLogin
)
from controllers.aluno_controller import (
    criar_aluno,
    verificar_token_cadastro,
    login,
    verificar_token_login,
    buscar_aluno_por_email,
    atualizar_email,
    atualizar_preferencias,
    excluir_aluno
)

router = APIRouter(prefix="/alunos", tags=["Alunos"])


@router.post("/")
def cadastrar_aluno(dados: AlunoCriar, db: Session = Depends(get_db)):
    return criar_aluno(db, dados)


@router.post("/verificar-cadastro")
def verificar_cadastro(dados: AlunoVerificarToken, db: Session = Depends(get_db)):
    return verificar_token_cadastro(db, dados.email, dados.token)



@router.post("/login")
def solicitar_login(dados: AlunoLogin, db: Session = Depends(get_db)):
    return login(db, dados.email)


@router.post("/login/verificar", response_model=AlunoResposta)
def verificar_login(dados: AlunoVerificarToken, db: Session = Depends(get_db)):
    return verificar_token_login(db, dados.email, dados.token)


@router.get("/{email}", response_model=AlunoResposta)
def buscar_aluno(email: str, db: Session = Depends(get_db)):
    return buscar_aluno_por_email(db, email)



@router.put("/{email}/email", response_model=AlunoResposta)
def editar_email(email: str, dados: AlunoAtualizarEmail, db: Session = Depends(get_db)):
    return atualizar_email(db, email, dados.novo_email)


@router.put("/{email}/preferencias", response_model=AlunoResposta)
def editar_preferencias(email: str, dados: AlunoAtualizarPreferencias, db: Session = Depends(get_db)):
    return atualizar_preferencias(db, email, dados.preferencias_tipos)


@router.delete("/{email}")
def deletar_aluno(email: str, db: Session = Depends(get_db)):
    return excluir_aluno(db, email)