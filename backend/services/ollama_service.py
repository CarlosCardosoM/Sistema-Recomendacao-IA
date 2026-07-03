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


def identificar_topico(
    pergunta: str,
    topicos: list[str],
    historico_recente: list[dict] | None = None
) -> str | None:
    """
    Pede ao LLM para escolher, dentre os tópicos já cadastrados no banco,
    qual é o tópico específico da pergunta mais recente do aluno.

    Existe porque a similaridade por embedding sozinha não discrimina bem
    subtópicos próximos do mesmo domínio (ex.: "Busca Cega" e "Busca A*"
    ficam a ~0.01 de distância no cosseno), o que fazia a busca por
    conteúdo relevante escorregar para o tópico errado.

    Recebe o histórico recente como turnos separados (não concatenado em
    uma única string) para que o LLM possa distinguir saudações e mensagens
    irrelevantes de perguntas de acompanhamento reais — concatenar texto
    cru (ex.: "Boa noite" + "Busca cega") dilui o sinal e piora a resposta.

    Retorna o nome exato do tópico ou None se a pergunta for genérica
    demais para apontar um tópico específico.
    """
    lista_topicos = "\n".join(f"- {t}" for t in topicos)

    bloco_historico = ""
    if historico_recente:
        linhas = "\n".join(
            f"{'Aluno' if h['role'] == 'usuario' else 'Assistente'}: {h['content']}"
            for h in historico_recente
        )
        bloco_historico = f"Histórico recente da conversa (apenas para contexto):\n{linhas}\n\n"

    prompt = f"""{bloco_historico}A pergunta mais recente do aluno abaixo é sobre algoritmos de busca em
Inteligência Artificial.

Escolha, dentre a lista de tópicos abaixo, qual é o tópico específico ao qual
a pergunta mais recente do aluno se refere. Use o histórico da conversa acima
somente para entender o contexto (por exemplo, se a pergunta é uma resposta
curta a algo que o assistente perguntou antes) — ignore saudações e mensagens
sem relação com o assunto.

Tópicos disponíveis:
{lista_topicos}

Se a pergunta não se referir claramente a nenhum desses tópicos específicos
(por exemplo, uma pergunta genérica sobre "algoritmos de busca" em geral),
responda exatamente: nenhum

Responda APENAS com o nome exato do tópico da lista, ou "nenhum". Sem explicações.

Pergunta mais recente do aluno: {pergunta}"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model":    MODELO_ANALISE,
            "messages": [{"role": "user", "content": prompt}],
            "stream":   False
        })
        response.raise_for_status()
        resposta = response.json()["message"]["content"].strip().lower()
        for topico in topicos:
            if topico.lower() in resposta:
                return topico
        return None
    except Exception as e:
        print("ERRO AO IDENTIFICAR TÓPICO:", e)
        return None


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