import numpy as np
from sqlalchemy.orm import Session

from database import Conteudo
from services.embedding_service import (
    gerar_embedding,
    bytes_para_embedding
)
from services.ollama_service import classificar_pergunta

TOP_K = 3

# Threshold para perguntas técnicas (sobre algoritmos, código, etc.)
THRESHOLD_TECNICO  = 0.45

# Threshold para perguntas genéricas (fora do escopo mas não é saudação)
THRESHOLD_GENERICO = 0.70


def calcular_similaridade(vetor1: np.ndarray, vetor2: np.ndarray) -> float:
    """
    Calcula a similaridade coseno entre dois vetores.
    Retorna um valor entre 0.0 e 1.0.
    """
    norma1 = np.linalg.norm(vetor1)
    norma2 = np.linalg.norm(vetor2)
    if norma1 == 0 or norma2 == 0:
        return 0.0
    return float(np.dot(vetor1, vetor2) / (norma1 * norma2))


def buscar_conteudos_relevantes(
    db: Session,
    embedding_pergunta: np.ndarray,
    pergunta: str = "",
    top_k: int = TOP_K
) -> list[tuple]:
    """
    Busca os conteúdos mais similares à pergunta no banco.

    Usa o LLM para classificar a pergunta antes de buscar:
    - Técnica  → threshold 0.45 (encontra mais conteúdos)
    - Genérica → threshold 0.70 (restritivo, evita ruído)

    Vantagem: funciona com qualquer idioma e variação de texto,
    sem depender de listas fixas de palavras.
    """
    # Classifica a pergunta usando o LLM
    eh_tecnica = classificar_pergunta(pergunta) if pergunta else False
    threshold = THRESHOLD_TECNICO if eh_tecnica else THRESHOLD_GENERICO

    conteudos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    resultados = []
    for conteudo in conteudos:
        vetor_conteudo = bytes_para_embedding(conteudo.embeddings)
        score = calcular_similaridade(embedding_pergunta, vetor_conteudo)
        if score >= threshold:
            resultados.append((conteudo, score))

    resultados.sort(key=lambda x: x[1], reverse=True)
    return resultados[:top_k]


def montar_contexto(conteudos_relevantes: list[tuple]) -> str:
    """
    Monta o texto de contexto para enviar ao Ollama junto com a pergunta.
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
    """
    return [
        {"role": mensagem.papel, "content": mensagem.conteudo}
        for mensagem in mensagens
    ]


def processar_pergunta(db: Session, pergunta: str, mensagens: list) -> dict:
    """
    Pipeline completo do RAG.
    """
    # 1. Gera o embedding da pergunta
    vetor_pergunta = gerar_embedding(pergunta)
    embedding_bytes = vetor_pergunta.tobytes()

    # 2. Busca conteúdos com threshold dinâmico via LLM
    conteudos_relevantes = buscar_conteudos_relevantes(
        db, vetor_pergunta, pergunta
    )

    # 3. Monta contexto e histórico
    contexto  = montar_contexto(conteudos_relevantes)
    historico = montar_historico(mensagens)

    return {
        "embedding_pergunta":   embedding_bytes,
        "conteudos_relevantes": conteudos_relevantes,
        "contexto":             contexto,
        "historico":            historico,
    }