from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import Interacao, Aluno, Conteudo
from controllers.aluno_controller import buscar_aluno_por_email


def abrir_conteudo(db: Session, email: str, conteudo_id: int) -> Interacao:
    """
    Registra que o aluno abriu um conteúdo.
    Segue a função abrirConteudo() do pseudocódigo.
    """
    aluno = buscar_aluno_por_email(db, email)

    conteudo = db.query(Conteudo).filter(Conteudo.id == conteudo_id).first()
    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado.")

    interacao = Interacao(
        aluno_id    = aluno.id,
        conteudo_id = conteudo_id,
        aberto_em   = datetime.now()
    )
    db.add(interacao)
    db.commit()
    db.refresh(interacao)
    return interacao


def fechar_conteudo(db: Session, interacao_id: int) -> Interacao:
    """
    Registra o fechamento do conteúdo e calcula o tempo de visualização.
    Segue a função fecharConteudo() do pseudocódigo.
    """
    interacao = db.query(Interacao).filter(Interacao.id == interacao_id).first()
    if not interacao:
        raise HTTPException(status_code=404, detail="Interação não encontrada.")

    if interacao.fechado_em is not None:
        raise HTTPException(status_code=400, detail="Esse conteúdo já foi fechado.")

    interacao.fechado_em = datetime.now()
    interacao.tempo_visualizacao = (
        interacao.fechado_em - interacao.aberto_em
    ).total_seconds()

    db.commit()
    db.refresh(interacao)
    return interacao


def listar_interacoes_aluno(db: Session, email: str) -> list:
    """
    Retorna o histórico de interações de um aluno.
    Equivalente ao historicoInteracoes do pseudocódigo.
    """
    aluno = buscar_aluno_por_email(db, email)

    interacoes = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).order_by(Interacao.aberto_em.desc()).all()

    return [
        {
            "id":                  i.id,
            "conteudo_id":         i.conteudo_id,
            "tempo_visualizacao":  i.tempo_visualizacao,
            "aberto_em":           i.aberto_em,
            "fechado_em":          i.fechado_em
        }
        for i in interacoes
    ]


def contar_conteudos_abertos(db: Session, email: str) -> int:
    """
    Conta quantos conteúdos o aluno já abriu.
    Equivalente ao quantidadeConteudosAbertos do pseudocódigo.
    """
    aluno = buscar_aluno_por_email(db, email)
    return db.query(Interacao).filter(Interacao.aluno_id == aluno.id).count()