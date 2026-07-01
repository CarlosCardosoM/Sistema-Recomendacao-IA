from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import Curtida, Conteudo
from controllers.aluno_controller import buscar_aluno_por_email


def curtir_conteudo(db: Session, email: str, conteudo_id: int) -> dict:
    """
    Registra a curtida de um aluno em um conteúdo.
    Segue a função registrarCurtida() do pseudocódigo.
    """
    aluno = buscar_aluno_por_email(db, email)

    conteudo = db.query(Conteudo).filter(Conteudo.id == conteudo_id).first()
    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado.")

    # Verifica se já curtiu antes
    curtida_existente = db.query(Curtida).filter(
        Curtida.aluno_id == aluno.id,
        Curtida.conteudo_id == conteudo_id
    ).first()

    if curtida_existente:
        raise HTTPException(status_code=400, detail="Conteúdo já curtido.")

    curtida = Curtida(aluno_id=aluno.id, conteudo_id=conteudo_id)
    db.add(curtida)
    db.commit()
    db.refresh(curtida)

    return {"mensagem": "Conteúdo curtido com sucesso."}


def remover_curtida(db: Session, email: str, conteudo_id: int) -> dict:
    """Remove a curtida de um aluno em um conteúdo."""
    aluno = buscar_aluno_por_email(db, email)

    curtida = db.query(Curtida).filter(
        Curtida.aluno_id == aluno.id,
        Curtida.conteudo_id == conteudo_id
    ).first()

    if not curtida:
        raise HTTPException(status_code=404, detail="Curtida não encontrada.")

    db.delete(curtida)
    db.commit()

    return {"mensagem": "Curtida removida com sucesso."}


def listar_curtidas_aluno(db: Session, email: str) -> list:
    """
    Retorna todos os conteúdos curtidos por um aluno.
    Equivalente a aluno.curtidas do pseudocódigo.
    """
    aluno = buscar_aluno_por_email(db, email)

    curtidas = db.query(Curtida).filter(Curtida.aluno_id == aluno.id).all()

    return [
        {"conteudo_id": c.conteudo_id}
        for c in curtidas
    ]


def verificar_curtida(db: Session, email: str, conteudo_id: int) -> bool:
    """
    Verifica se um aluno curtiu um conteúdo específico.
    Usado no calcularScore() — scoreCurtida.
    """
    aluno = buscar_aluno_por_email(db, email)

    curtida = db.query(Curtida).filter(
        Curtida.aluno_id == aluno.id,
        Curtida.conteudo_id == conteudo_id
    ).first()

    return curtida is not None