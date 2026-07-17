import requests
import json

OLLAMA_URL     = "http://localhost:11434/api/chat"
MODELO_CHAT    = "chatbootIA"
MODELO_ANALISE = "llama3.2"


def gerar_resposta(pergunta: str, contexto: str, historico: list) -> str:

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
        "stream":   False,
        # Limita o tamanho da resposta — sem isso, uma geração que entra em
        # loop de repetição nunca para sozinha e trava o único slot de
        # execução do Ollama, deixando toda pergunta seguinte na fila.
        "options":  {"num_predict": 700}
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
            "stream":   False,
            # temperature baixa: essa chamada é uma classificação/extração
            # estruturada, não geração de texto livre — sem isso o Ollama
            # usa o default (~0.8) e a mesma pergunta pode sair classificada
            # de formas diferentes em execuções distintas.
            "options":  {"num_predict": 150, "temperature": 0.1}
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


def analisar_intencao(
    pergunta: str,
    topicos: list[str],
    tipos: list[str],
    historico_recente: list[dict] | None = None
) -> dict:
    """
    Uma única chamada ao LLM que substitui três chamadas separadas
    (classificar técnica/genérica, identificar tópico, identificar tipo
    de conteúdo pedido). Antes cada uma era um roundtrip sequencial ao
    Ollama só pra montar a busca — juntas, adicionavam vários segundos de
    espera por pergunta. Aqui tudo sai em um JSON só.

    Recebe o histórico recente como turnos separados (não concatenado em
    uma única string) para que o LLM possa distinguir saudações e mensagens
    irrelevantes de perguntas de acompanhamento reais — concatenar texto
    cru (ex.: "Boa noite" + "Busca cega") dilui o sinal e piora a resposta.

    Retorna {"categoria": "tecnica"|"saudacao"|"fora_do_escopo",
             "topico": str|None, "tipo": str|None}.
    """
    lista_topicos = "\n".join(f"- {t}" for t in topicos)
    lista_tipos    = "\n".join(f"- {t}" for t in tipos)

    bloco_historico = ""
    if historico_recente:
        linhas = "\n".join(
            f"{'Aluno' if h['role'] == 'usuario' else 'Assistente'}: {h['content']}"
            for h in historico_recente
        )
        bloco_historico = f"Histórico recente da conversa (apenas para contexto):\n{linhas}\n\n"

    prompt = f"""{bloco_historico}Analise a pergunta mais recente do aluno abaixo e responda APENAS com um
JSON válido, sem nenhum texto antes ou depois, no formato exato:

{{
  "categoria": "tecnica" ou "saudacao" ou "fora_do_escopo",
  "topico": "nome exato de um tópico da lista, ou null",
  "tipo": "nome exato de um tipo da lista, ou null"
}}

"categoria":
- "tecnica": pergunta sobre algoritmos de busca, inteligência artificial,
  grafos, código, programação ou conteúdo educacional de computação.
- "saudacao": cumprimento ou conversa fiada, SEM pedir nenhum conteúdo,
  explicação ou tarefa (ex.: "oi", "boa noite", "tudo bem?", "obrigado",
  "valeu", "até mais"). Se a mensagem pede pra explicar, escrever, resolver,
  traduzir ou ajudar com qualquer coisa, NÃO é saudação.
- "fora_do_escopo": pede conteúdo, explicação, tarefa ou ajuda com qualquer
  assunto que não seja algoritmos de busca em IA — mesmo que pareça inofensivo
  (ex.: outra matéria escolar, escrever um texto/poema/redação, resolver
  conta de matemática, receita, tradução, piada, código não relacionado ao
  curso, qualquer outro tópico de conhecimento geral).

Regra prática: se a mensagem pede pra você FAZER ou EXPLICAR alguma coisa
que não é sobre algoritmos de busca em IA, é "fora_do_escopo", nunca
"saudacao" — "saudacao" é só pra mensagens que não pedem nada.

"topico": escolha dentre a lista abaixo qual é o tópico específico ao qual
a pergunta se refere (use o histórico da conversa só para entender
referências, ex.: uma resposta curta a algo que o assistente perguntou
antes). Se não apontar claramente pra um tópico específico, use null.
Tópicos disponíveis:
{lista_topicos}

"tipo": null é o valor mais comum — a GRANDE maioria das perguntas não pede
um tipo de conteúdo específico e deve usar null. Só preencha um tipo da
lista quando o aluno pedir explicitamente por aquele formato de material
(a própria palavra ou um sinônimo direto dela aparece na pergunta).
Tipos disponíveis:
{lista_tipos}

Exemplos:
- "O que é busca em largura?" → null (pergunta teórica, não pede formato)
- "Como funciona o algoritmo A*?" → null (pergunta teórica)
- "Quais as vantagens da busca gulosa?" → null (pergunta teórica)
- "Me indique atividades/exercícios sobre busca cega" → atividade (pediu exercício explicitamente)
- "Tem algum vídeo sobre isso?" → video (pediu vídeo explicitamente)
- "Quero um artigo pra ler sobre o assunto" → artigo (pediu artigo explicitamente)

Na dúvida, use null.

Pergunta mais recente do aluno: {pergunta}"""

    padrao = {"categoria": "tecnica", "topico": None, "tipo": None}

    try:
        response = requests.post(OLLAMA_URL, json={
            "model":    MODELO_ANALISE,
            "messages": [{"role": "user", "content": prompt}],
            "format":   "json",
            "stream":   False,

            "options":  {"num_predict": 100, "temperature": 0.1}
        })
        response.raise_for_status()
        resultado = json.loads(response.json()["message"]["content"])

        def _casar(valor, opcoes):
            if not isinstance(valor, str):
                return None
            valor_norm = valor.strip().lower()
            return next((o for o in opcoes if o.lower() == valor_norm), None)

        topico = _casar(resultado.get("topico"), topicos)
        tipo   = _casar(resultado.get("tipo"), tipos)

        categoria = resultado.get("categoria")
        if categoria not in ("tecnica", "saudacao", "fora_do_escopo"):
            categoria = "tecnica"

        if topico is not None:
            categoria = "tecnica"

        return {
            "categoria": categoria,
            "topico":    topico,
            "tipo":      tipo,
        }
    except Exception as e:
        print("ERRO AO ANALISAR INTENÇÃO DA PERGUNTA:", e)
        return padrao