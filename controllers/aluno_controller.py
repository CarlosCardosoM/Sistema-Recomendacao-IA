import bcrypt
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import Aluno
from schemas.aluno_schema import AlunoCriar


def criptografar_senha(senha: str) -> str:
    """Gera o hash da senha usando bcrypt."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")



def criar_aluno(db: Session, dados: AlunoCriar) -> Aluno:
    email_existente = db.query(Aluno).filter(Aluno.email == dados.email).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    senha_hash = criptografar_senha(dados.senha)

    aluno = Aluno(
        nome=dados.nome,
        email=dados.email,
        senha=senha_hash,
        preferencias_tipos=dados.preferencias_tipos
    )
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno



def buscar_aluno_por_email(db: Session, email: str) -> Aluno:
    aluno = db.query(Aluno).filter(Aluno.email == email).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    return aluno

