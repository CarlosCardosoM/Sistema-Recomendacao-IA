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
PESO_DIFICULDADE    = 0.10

# Tempo de referência para normalizar o score de tempo (em segundos)
TEMPO_REFERENCIA = 300  # 5 minutos


def normalizar_texto(texto: str | None) -> str | None:
    """
    Remove acentos e converte para minúsculo.
    Usado para comparar nivel_dificuldade de forma confiável,
    já que o Ollama pode retornar "intermediário" em vez de "intermediario".
    """
    if texto is None:
        return None
    texto_sem_acento = unicodedata.normalize("NFKD", texto)
    texto_sem_acento = "".join(c for c in texto_sem_acento if not unicodedata.combining(c))
    return texto_sem_acento.lower().strip()


def normalizar_tempo(tempo_segundos: float | None) -> float:
    """
    Normaliza o tempo de visualização para um valor entre 0 e 1.
    Usa TEMPO_REFERENCIA como o tempo "ideal" de leitura.
    """
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
    Segue exatamente a função calcularScore() do pseudocódigo.
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

    # 5. Tempo de visualização normalizado (se já abriu esse conteúdo)
    score_tempo = 0.0
    if interacao_existente:
        score_tempo = normalizar_tempo(interacao_existente.tempo_visualizacao)

    # 6. Quantidade total de conteúdos que o aluno já abriu
    quantidade_abertos = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).count()
    score_interacao = min(quantidade_abertos * 0.1, 1.0)

    # 7. Compatibilidade de nível de dificuldade com a análise da pergunta
    score_dificuldade = 0.0
    if nivel_pergunta and normalizar_texto(nivel_pergunta) == normalizar_texto(conteudo.nivel_dificuldade):
        score_dificuldade = 1.0

    # Soma ponderada final
    score_final = (
        PESO_SIMILARIDADE * score_similaridade +
        PESO_PREFERENCIA  * score_preferencia +
        PESO_CURTIDA      * score_curtida +
        PESO_HISTORICO    * score_historico +
        PESO_TEMPO        * score_tempo +
        PESO_INTERACAO    * score_interacao +
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
    Segue a função recomendarConteudo() do pseudocódigo.

    A quantidade de recomendações aumenta conforme o aluno
    abre mais conteúdos no sistema.
    """
    aluno = db.query(Aluno).filter(Aluno.email == email).first()
    if not aluno:
        return []

    # Busca todos os conteúdos que já têm embedding gerado
    candidatos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    # Calcula o score de cada candidato
    lista_scores = []
    for conteudo in candidatos:
        score = calcular_score(db, aluno, conteudo, embedding_pergunta, nivel_pergunta)
        lista_scores.append((conteudo, score))

    # Ordena por score decrescente
    lista_scores.sort(key=lambda x: x[1], reverse=True)

    # Define quantas recomendações mostrar com base no engajamento do aluno
    quantidade_abertos = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).count()

    if quantidade_abertos <= 2:
        quantidade_recomendacoes = 1
    elif quantidade_abertos <= 5:
        quantidade_recomendacoes = 2
    else:
        quantidade_recomendacoes = 3

    top_recomendacoes = lista_scores[:quantidade_recomendacoes]

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