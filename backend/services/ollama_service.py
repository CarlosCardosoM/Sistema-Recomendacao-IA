import requests
import json

OLLAMA_URL        = "http://localhost:11434/api/chat"
MODELO_CHAT       = "chatbootIA"   # modelo criado pelo seu Modelfile
MODELO_ANALISE    = "llama3.2"     # modelo base — usado só para extrair JSON


def gerar_resposta(pergunta: str, contexto: str, historico: list) -> str:
    """
    Envia a pergunta do aluno ao EduBot com o contexto do RAG
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


def analisar_pergunta(pergunta: str) -> dict:
    """
    Analisa a pergunta do aluno e extrai tópico, subtópicos,
    assunto geral e nível de dificuldade.

    Segue a análise feita dentro de responderPergunta() no pseudocódigo.
    Usa o llama3.2 base (sem a persona do EduBot) com saída forçada em JSON,
    já que essa chamada é só para extração de dados estruturados.

    Returns:
        dict com: topico_principal, subtopicos, assunto_geral, nivel_dificuldade
        ou valores None em caso de falha na análise
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
        # Se a análise falhar, o sistema continua funcionando
        # apenas sem o score de dificuldade
        return {
            "topico_principal":  None,
            "subtopicos":        None,
            "assunto_geral":     None,
            "nivel_dificuldade": None
        }