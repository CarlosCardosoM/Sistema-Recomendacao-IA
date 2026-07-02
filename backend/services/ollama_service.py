import requests
import json

OLLAMA_URL     = "http://localhost:11434/api/chat"
MODELO_CHAT    = "chatbootIA"
MODELO_ANALISE = "llama3.2"


def gerar_resposta(pergunta: str, contexto: str, historico: list) -> str:
    """
    Envia a pergunta ao EduBot com o contexto do RAG e histórico da conversa.
    """
    mensagem_com_contexto = f"""Contexto com conteúdos relevantes:
{contexto}

Pergunta do aluno:
{pergunta}"""

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


def analisar_pergunta(pergunta: str) -> dict:
    """
    Analisa a pergunta e extrai tópico, subtópicos, assunto e nível de dificuldade.
    Retorna JSON estruturado.
    """
    prompt = f"""Analise a pergunta abaixo sobre algoritmos de busca em Inteligência Artificial
e responda APENAS com um JSON válido, sem nenhum texto antes ou depois, no formato exato:

{{
  "topico_principal": "string curta",
  "subtopicos": "string separada por vírgula",
  "assunto_geral": "string curta",
  "nivel_dificuldade": "basico ou intermediario"
}}

Pergunta: {pergunta}"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model":    MODELO_ANALISE,
            "messages": [{"role": "user", "content": prompt}],
            "format":   "json",
            "stream":   False
        })
        response.raise_for_status()
        conteudo = response.json()["message"]["content"]
        analise = json.loads(conteudo)
        return {
            "topico_principal":  analise.get("topico_principal"),
            "subtopicos":        analise.get("subtopicos"),
            "assunto_geral":     analise.get("assunto_geral"),
            "nivel_dificuldade": analise.get("nivel_dificuldade")
        }
    except Exception as e:
        print("ERRO NA ANÁLISE DA PERGUNTA:", e)
        return {
            "topico_principal":  None,
            "subtopicos":        None,
            "assunto_geral":     None,
            "nivel_dificuldade": None
        }


def classificar_pergunta(pergunta: str) -> bool:
    """
    Usa o LLM para decidir se a pergunta é técnica ou genérica.

    Retorna True  → pergunta técnica (busca no RAG com threshold baixo)
    Retorna False → saudação ou mensagem genérica (sem recomendação)

    Vantagem sobre lista de palavras: funciona com qualquer idioma,
    gírias, variações ortográficas e frases que não estão em listas fixas.
    Em caso de erro, assume True para não bloquear perguntas legítimas.
    """
    prompt = f"""Responda APENAS com "sim" ou "nao", sem nenhum outro texto.

A pergunta abaixo é sobre algoritmos de busca, inteligência artificial,
grafos, código, programação ou conteúdo educacional de computação?

Pergunta: {pergunta}

Responda apenas: sim ou nao"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model":    MODELO_ANALISE,
            "messages": [{"role": "user", "content": prompt}],
            "stream":   False
        })
        response.raise_for_status()
        resposta = response.json()["message"]["content"].strip().lower()
        return "sim" in resposta
    except Exception as e:
        print("ERRO NA CLASSIFICAÇÃO DA PERGUNTA:", e)
        return True  # em caso de erro, assume técnica e busca normalmente