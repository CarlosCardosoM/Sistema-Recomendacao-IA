from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import Aluno
from schemas.aluno_schema import AlunoCriar
from services.email_service import gerar_token, enviar_email_verificacao


def criar_aluno(db: Session, dados: AlunoCriar) -> dict:
    # Verifica se o email já está cadastrado
    email_existente = db.query(Aluno).filter(Aluno.email == dados.email).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    # Gera o token de verificação
    token = gerar_token()
    token_expira_em = datetime.now() + timedelta(minutes=10)

    # Cria e salva o aluno
    aluno = Aluno(
        nome=dados.nome,
        email=dados.email,
        preferencias_tipos=dados.preferencias_tipos,
    )
    aluno.token = token
    aluno.token_expira_em = token_expira_em

    db.add(aluno)
    db.commit()
    db.refresh(aluno)

    # Envia o email com o código
    enviar_email_verificacao(aluno.email, token, aluno.nome)

    return {"mensagem": f"Conta criada! Verifique o email {aluno.email} para confirmar o cadastro."}


def verificar_token_cadastro(db: Session, email: str, token: str) -> dict:
    aluno = buscar_aluno_por_email(db, email)

    # Verifica se o token está correto
    if aluno.token != token:
        raise HTTPException(status_code=400, detail="Código inválido.")

    # Verifica se o token não expirou
    if datetime.now() > aluno.token_expira_em:
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    # Limpa o token após verificação
    aluno.token = None
    aluno.token_expira_em = None
    db.commit()

    return {"mensagem": "Cadastro confirmado com sucesso!"}


def login(db: Session, email: str) -> dict:
    aluno = buscar_aluno_por_email(db, email)

    # Gera novo token de login
    token = gerar_token()
    token_expira_em = datetime.now() + timedelta(minutes=10)

    aluno.token = token
    aluno.token_expira_em = token_expira_em
    db.commit()

    # Envia o email com o código
    enviar_email_verificacao(aluno.email, token, aluno.nome)

    return {"mensagem": f"Código enviado para {aluno.email}. Válido por 10 minutos."}


def verificar_token_login(db: Session, email: str, token: str) -> Aluno:
    aluno = buscar_aluno_por_email(db, email)

    # Verifica se o token está correto
    if aluno.token != token:
        raise HTTPException(status_code=400, detail="Código inválido.")

    # Verifica se o token não expirou
    if datetime.now() > aluno.token_expira_em:
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    # Limpa o token após login
    aluno.token = None
    aluno.token_expira_em = None
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


def atualizar_preferencias(db: Session, email: str, preferencias: str) -> Aluno:
    aluno = buscar_aluno_por_email(db, email)
    aluno.preferencias_tipos = preferencias
    db.commit()
    db.refresh(aluno)
    return aluno

def excluir_aluno(db: Session, email: str) -> dict:
    aluno = buscar_aluno_por_email(db, email)
    db.delete(aluno)
    db.commit()
    return {"mensagem": "Aluno excluído com sucesso."}