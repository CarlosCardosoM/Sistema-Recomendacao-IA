import requests
import numpy as np

OLLAMA_URL        = "http://localhost:11434/api/embeddings"
MODELO_EMBEDDING  = "nomic-embed-text"


def gerar_embedding(texto: str) -> np.ndarray:
    """
    Gera o embedding de um texto usando o nomic-embed-text via Ollama.

    Args:
        texto: texto a ser transformado em vetor

    Returns:
        vetor numpy float32
    """
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
    """
    Gera o embedding da pergunta do aluno.
    Usado em responderPergunta() — salvo na tabela Mensagem.

    Args:
        pergunta: texto digitado pelo aluno

    Returns:
        embedding serializado como bytes para salvar no banco
    """
    vetor = gerar_embedding(pergunta)
    return embedding_para_bytes(vetor)


def gerar_embedding_conteudo(conteudo) -> bytes:
    """
    Gera o embedding de um conteúdo concatenando os campos relevantes.
    Segue a função gerarEmbeddingConteudo() do pseudocódigo.

    Args:
        conteudo: objeto Conteudo do banco ou dicionário do JSON

    Returns:
        embedding serializado como bytes para salvar no banco
    """
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