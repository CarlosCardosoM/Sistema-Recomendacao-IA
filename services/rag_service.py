import numpy as np
from sqlalchemy.orm import Session

from database import Conteudo
from services.embedding_service import (
    gerar_embedding,
    gerar_embedding_pergunta,
    bytes_para_embedding
)


# Quantidade de conteúdos relevantes recuperados por busca
TOP_K = 3


def calcular_similaridade(vetor1: np.ndarray, vetor2: np.ndarray) -> float:
    """
    Calcula a similaridade coseno entre dois vetores.
    Retorna um valor entre 0.0 e 1.0 — quanto maior, mais similar.
    """
    norma1 = np.linalg.norm(vetor1)
    norma2 = np.linalg.norm(vetor2)

    if norma1 == 0 or norma2 == 0:
        return 0.0

    return float(np.dot(vetor1, vetor2) / (norma1 * norma2))


def buscar_conteudos_relevantes(
    db: Session,
    embedding_pergunta: np.ndarray,
    top_k: int = TOP_K
) -> list[tuple]:
    """
    Busca os conteúdos mais similares à pergunta no banco.
    Retorna lista de tuplas (conteudo, score) ordenada por score decrescente.
    """
    conteudos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    resultados = []
    for conteudo in conteudos:
        vetor_conteudo = bytes_para_embedding(conteudo.embeddings)
        score = calcular_similaridade(embedding_pergunta, vetor_conteudo)
        resultados.append((conteudo, score))

    # Ordena por score decrescente e retorna os top_k
    resultados.sort(key=lambda x: x[1], reverse=True)
    return resultados[:top_k]


def montar_contexto(conteudos_relevantes: list[tuple]) -> str:
    """
    Monta o texto de contexto a partir dos conteúdos recuperados
    para ser enviado ao Ollama junto com a pergunta.
    """
    if not conteudos_relevantes:
        return "Nenhum conteúdo relevante encontrado na base."

    contexto = ""
    for i, (conteudo, score) in enumerate(conteudos_relevantes, start=1):
        contexto += f"""
[Conteúdo {i}] — similaridade: {score:.2f}
Título: {conteudo.titulo}
Tópico: {conteudo.topico_principal}
Descrição: {conteudo.descricao}
Link: {conteudo.link}
---"""
    return contexto.strip()


def montar_historico(mensagens: list) -> list[dict]:
    """
    Converte as mensagens da sessão para o formato que o Ollama entende.

    Args:
        mensagens: lista de objetos Mensagem do banco

    Returns:
        [{"role": "user", "content": "..."}, ...]
    """
    return [
        {"role": mensagem.papel, "content": mensagem.conteudo}
        for mensagem in mensagens
    ]


def processar_pergunta(db: Session, pergunta: str, mensagens: list) -> dict:
    """
    Pipeline completo do RAG — do texto da pergunta até o contexto montado.
    Segue a função responderPergunta() do pseudocódigo.

    Args:
        db:        sessão do banco
        pergunta:  texto digitado pelo aluno
        mensagens: histórico de mensagens da sessão

    Returns:
        dicionário com:
            - embedding_pergunta: bytes para salvar no banco
            - conteudos_relevantes: lista de (conteudo, score)
            - contexto: texto montado para enviar ao Ollama
            - historico: histórico formatado para o Ollama
    """
    # 1. Gera o embedding da pergunta
    vetor_pergunta = gerar_embedding(pergunta)
    embedding_bytes = vetor_pergunta.tobytes()

    # 2. Busca os conteúdos mais relevantes no banco
    conteudos_relevantes = buscar_conteudos_relevantes(db, vetor_pergunta)

    # 3. Monta o contexto com os conteúdos recuperados
    contexto = montar_contexto(conteudos_relevantes)

    # 4. Monta o histórico da conversa
    historico = montar_historico(mensagens)

    return {
        "embedding_pergunta":  embedding_bytes,
        "conteudos_relevantes": conteudos_relevantes,
        "contexto":            contexto,
        "historico":           historico,
    }