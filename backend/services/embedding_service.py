import requests
import numpy as np

OLLAMA_URL        = "http://localhost:11434/api/embeddings"
MODELO_EMBEDDING  = "nomic-embed-text"


def gerar_embedding(texto: str) -> np.ndarray:

    response = requests.post(OLLAMA_URL, json={
        "model":  MODELO_EMBEDDING,
        "prompt": texto
    })
    response.raise_for_status()

    vetor = response.json()["embedding"]
    return np.array(vetor, dtype=np.float32)


def embedding_para_bytes(vetor: np.ndarray) -> bytes:
    """
    Serializa o vetor para salvar no banco como blob.
    Usado em: indexar_conteudos.py e ao salvar embedding da pergunta.
    """
    return vetor.tobytes()


def bytes_para_embedding(blob: bytes) -> np.ndarray:
    """
    Desserializa o blob do banco de volta para vetor numpy.
    Usado em: rag_service.py ao recuperar embeddings dos conteúdos.
    """
    return np.frombuffer(blob, dtype=np.float32)

def gerar_embedding_pergunta(pergunta: str) -> bytes:

    vetor = gerar_embedding(pergunta)
    return embedding_para_bytes(vetor)


def gerar_embedding_conteudo(conteudo) -> bytes:
    
    if isinstance(conteudo, dict):
        texto = " ".join([
            conteudo.get("titulo", ""),
            conteudo.get("descricao", ""),
            conteudo.get("topico_principal", ""),
            conteudo.get("palavras_chave", ""),
        ])
    else:
        texto = " ".join([
            conteudo.titulo or "",
            conteudo.descricao or "",
            conteudo.topico_principal or "",
            conteudo.palavras_chave or "",
        ])

    vetor = gerar_embedding(texto)
    return embedding_para_bytes(vetor)