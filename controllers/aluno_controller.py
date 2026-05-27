import bcrypt
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import Aluno
from schemas.aluno_schema import AlunoCriar


def criptografar_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_aluno(db: Session, dados: AlunoCriar) -> Aluno:
    email_existente = db.query(Aluno).filter(Aluno.email == dados.email).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    aluno = Aluno(
        nome=dados.nome,
        email=dados.email,
        senha=criptografar_senha(dados.senha),
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


def atualizar_email(db: Session, email_atual: str, novo_email: str) -> Aluno:
    email_existente = db.query(Aluno).filter(Aluno.email == novo_email).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    aluno = buscar_aluno_por_email(db, email_atual)
    aluno.email = novo_email
    db.commit()
    db.refresh(aluno)
    return aluno


def atualizar_senha(db: Session, email: str, senha_atual: str, nova_senha: str) -> Aluno:
    aluno = buscar_aluno_por_email(db, email)
    if not verificar_senha(senha_atual, aluno.senha):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    aluno.senha = criptografar_senha(nova_senha)
    db.commit()
    db.refresh(aluno)
    return aluno


def atualizar_preferencias(db: Session, email: str, preferencias: str) -> Aluno:
    aluno = buscar_aluno_por_email(db, email)
    aluno.preferencias_tipos = preferencias
    db.commit()
    db.refresh(aluno)
    return aluno