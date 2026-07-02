import unicodedata
import numpy as np
from sqlalchemy.orm import Session

from database import Aluno, Conteudo, Interacao, Curtida
from services.embedding_service import bytes_para_embedding
from services.rag_service import calcular_similaridade

# Pesos do scoreFinal — conforme o pseudocódigo original
PESO_SIMILARIDADE  = 0.35
PESO_PREFERENCIA   = 0.20
PESO_CURTIDA       = 0.10
PESO_HISTORICO     = 0.10
PESO_TEMPO         = 0.10
PESO_INTERACAO     = 0.05
PESO_DIFICULDADE   = 0.10

TEMPO_REFERENCIA = 300  # 5 minutos
SCORE_MINIMO_RECOMENDACAO = 0.30


def normalizar_texto(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto_sem_acento = unicodedata.normalize("NFKD", texto)
    texto_sem_acento = "".join(
        c for c in texto_sem_acento if not unicodedata.combining(c)
    )
    return texto_sem_acento.lower().strip()


def normalizar_tempo(tempo_segundos: float | None) -> float:
    if tempo_segundos is None:
        return 0.0
    return min(tempo_segundos / TEMPO_REFERENCIA, 1.0)


def calcular_score(
    db: Session,
    aluno: Aluno,
    conteudo: Conteudo,
    embedding_pergunta: np.ndarray,
    nivel_pergunta: str | None
) -> float:
    """
    Calcula o score final de relevância de um conteúdo para um aluno.
    Combina 7 fatores ponderados conforme o pseudocódigo original.
    """

    # 1. Similaridade semântica entre a pergunta e o conteúdo
    embedding_conteudo = bytes_para_embedding(conteudo.embeddings)
    score_similaridade = calcular_similaridade(embedding_pergunta, embedding_conteudo)

    # 2. Preferência de tipo de conteúdo do aluno
    score_preferencia = 0.0
    if aluno.preferencias_tipos and conteudo.tipo in aluno.preferencias_tipos.split(","):
        score_preferencia = 1.0

    # 3. Se o aluno já curtiu esse conteúdo
    curtida = db.query(Curtida).filter(
        Curtida.aluno_id == aluno.id,
        Curtida.conteudo_id == conteudo.id
    ).first()
    score_curtida = 1.0 if curtida else 0.0

    # 4. Se o aluno já interagiu com esse conteúdo antes
    interacao_existente = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id,
        Interacao.conteudo_id == conteudo.id
    ).first()
    score_historico = 0.5 if interacao_existente else 0.0

    # 5. Tempo de visualização normalizado
    score_tempo = 0.0
    if interacao_existente:
        score_tempo = normalizar_tempo(interacao_existente.tempo_visualizacao)

    # 6. Quantidade total de conteúdos que o aluno já abriu
    # Este valor também define quantas recomendações serão exibidas
    quantidade_abertos = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).count()
    score_interacao = min(quantidade_abertos * 0.1, 1.0)

    # 7. Compatibilidade de nível de dificuldade com a análise da pergunta
    score_dificuldade = 0.0
    if nivel_pergunta and normalizar_texto(nivel_pergunta) == normalizar_texto(conteudo.nivel_dificuldade):
        score_dificuldade = 1.0

    score_final = (
        PESO_SIMILARIDADE * score_similaridade +
        PESO_PREFERENCIA  * score_preferencia  +
        PESO_CURTIDA      * score_curtida       +
        PESO_HISTORICO    * score_historico     +
        PESO_TEMPO        * score_tempo         +
        PESO_INTERACAO    * score_interacao     +
        PESO_DIFICULDADE  * score_dificuldade
    )
    return score_final


def recomendar_conteudo(
    db: Session,
    email: str,
    embedding_pergunta: np.ndarray,
    nivel_pergunta: str | None = None
) -> list[dict]:
    """
    Gera a lista de conteúdos recomendados para o aluno.

    A quantidade de recomendações aumenta conforme o aluno
    ABRE conteúdos recomendados (tabela Interacao) — quanto mais
    o aluno interage com os conteúdos, mais recomendações recebe.

    Lógica do pseudocódigo original:
    - <= 2 conteúdos abertos → 1 recomendação  (aluno novo)
    - <= 5 conteúdos abertos → 2 recomendações (engajamento médio)
    - >  5 conteúdos abertos → 3 recomendações (aluno engajado)
    """
    aluno = db.query(Aluno).filter(Aluno.email == email).first()
    if not aluno:
        return []

    candidatos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    lista_scores = []
    for conteudo in candidatos:
        score = calcular_score(db, aluno, conteudo, embedding_pergunta, nivel_pergunta)
        lista_scores.append((conteudo, score))

    lista_scores.sort(key=lambda x: x[1], reverse=True)

    # ── Quantidade baseada em conteúdos ABERTOS (Interacao) ──
    # O aluno usa POST /interacoes/abrir quando abre um conteúdo recomendado
    # Cada abertura registra uma Interacao → aumenta as recomendações futuras
    quantidade_abertos = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).count()

    if quantidade_abertos <= 2:
        quantidade_recomendacoes = 1
    elif quantidade_abertos <= 5:
        quantidade_recomendacoes = 2
    else:
        quantidade_recomendacoes = 3

    # Filtra por score mínimo — não recomenda conteúdo irrelevante
    top_recomendacoes = [
        (c, s) for c, s in lista_scores[:quantidade_recomendacoes]
        if s >= SCORE_MINIMO_RECOMENDACAO
    ]

    return [
        {
            "conteudo_id": conteudo.id,
            "titulo":      conteudo.titulo,
            "tipo":        conteudo.tipo,
            "link":        conteudo.link,
            "score":       round(score, 3)
        }
        for conteudo, score in top_recomendacoes
    ]