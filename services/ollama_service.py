import requests

OLLAMA_URL        = "http://localhost:11434/api/chat"
MODELO_CHAT       = "chatbootIA"  


def gerar_resposta(pergunta: str, contexto: str, historico: list) -> str:
    """
    Envia a pergunta do aluno ao ChatbootIA com o contexto do RAG
    e o histórico da conversa.

    Args:
        pergunta:  texto digitado pelo aluno
        contexto:  trechos de conteúdo recuperados pelo RAG
        historico: lista de mensagens anteriores da sessão
                   [{"role": "user", "content": "..."}, ...]

    Returns:
        resposta gerada pelo modelo como string
    """

    # Monta a mensagem com o contexto do RAG
    mensagem_com_contexto = f"""Contexto com conteúdos relevantes:
{contexto}

Pergunta do aluno:
{pergunta}"""

    # Monta o histórico completo para enviar ao Ollama
    mensagens = historico + [
        {"role": "user", "content": mensagem_com_contexto}
    ]

    response = requests.post(OLLAMA_URL, json={
        "model":    MODELO_CHAT,
        "messages": mensagens,
        "stream":   False
    })
    response.raise_for_status()

    return response.json()["message"]["content"]