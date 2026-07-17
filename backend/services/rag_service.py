import numpy as np
from sqlalchemy.orm import Session

from database import Conteudo
from services.embedding_service import (
    gerar_embedding,
    bytes_para_embedding
)
from services.ollama_service import analisar_intencao

TOP_K_CONTEXTO = 3       # quantos conteúdos vão no prompt do LLM (resposta)
TOP_K_CANDIDATOS = 8     # pool mais amplo, só pra recomendação escolher de dentro

# Threshold para perguntas técnicas (sobre algoritmos, código, etc.)
THRESHOLD_TECNICO  = 0.45

# Threshold para perguntas genéricas (fora do escopo mas não é saudação)
THRESHOLD_GENERICO = 0.70

# Margem de relevância relativa: descarta resultados muito piores que o
# melhor match, para não "completar" o top_k com conteúdo fora do tópico
MARGEM_RELEVANCIA = 0.12

# Tópicos cadastrados no banco, com as variações (PT/EN) usadas em
# topico_principal. A similaridade por embedding não discrimina bem
# subtópicos próximos (ex.: "Busca Cega" x "Busca A*" ficam a ~0.01 de
# distância), então usamos o LLM para identificar o tópico exato e
# restringir a busca a ele antes de rankear por similaridade.
TOPICOS_ALIASES = {
    "Busca Cega":            ["Busca Cega", "Blind Search"],
    "Busca Informada":       ["Busca Informada", "Informed Search"],
    "Busca A*":              ["Busca A*", "A* Search"],
    "Busca Gulosa":          ["Busca Gulosa", "Greedy Search"],
    "Busca Custo Uniforme":  ["Busca Custo Uniforme", "Uniform Cost Search"],
    "Busca em Largura":      ["Busca em Largura", "Breadth-First Search"],
    "Busca em Profundidade": ["Busca em Profundidade", "Depth-First Search"],
    "Busca Competitiva":     ["Busca Competitiva", "Competitive Search"],
}

# Tipos de conteúdo cadastrados no banco (ver Conteudo.tipo)
TIPOS_DISPONIVEIS = ["atividade", "video", "artigo", "livro", "codigo"]

# Rede de segurança: se a pergunta contém um desses termos, ela é
# claramente sobre algoritmos de busca — não deixamos o classificador do
# LLM (modelo pequeno, sem persona, roda em CPU) rotular como
# "fora_do_escopo" por ruído numa execução isolada. Não substitui o LLM
# (que ainda identifica tópico/tipo), só evita a recusa indevida.
PALAVRAS_CHAVE_TECNICO = [
    "busca", "bfs", "dfs", "a*", "a-star", "minimax", "alfa-beta",
    "alpha-beta", "poda", "heuristica", "heurística", "gulosa",
    "custo uniforme", "largura", "profundidade", "grafo", "algoritmo",
    "nó", "no ", "fronteira", "estado", "espaço de busca", "espaco de busca",
]


def _contem_palavra_chave_tecnica(pergunta: str) -> bool:
    pergunta_norm = pergunta.lower()
    return any(termo in pergunta_norm for termo in PALAVRAS_CHAVE_TECNICO)


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
    mensagens: list | None = None,
    top_k: int = TOP_K_CANDIDATOS
) -> tuple[list[tuple], str]:
    """
    Retorna (resultados, categoria) — categoria é "tecnica", "saudacao" ou
    "fora_do_escopo", pra quem chama decidir se deve gerar uma resposta
    normal ou recusar (ver chat_controller.responder_pergunta).
    """
    historico_recente = None
    if mensagens:
        historico_recente = [
            {"role": m.papel, "content": m.conteudo} for m in mensagens[-4:]
        ]

    intencao = (
        analisar_intencao(pergunta, list(TOPICOS_ALIASES.keys()), TIPOS_DISPONIVEIS, historico_recente)
        if pergunta else {"categoria": "saudacao", "topico": None, "tipo": None}
    )
    categoria = intencao["categoria"]

    if categoria == "fora_do_escopo" and pergunta and _contem_palavra_chave_tecnica(pergunta):
        categoria = "tecnica"

    threshold = THRESHOLD_TECNICO if categoria == "tecnica" else THRESHOLD_GENERICO

    conteudos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    if intencao["topico"]:
        aliases = TOPICOS_ALIASES[intencao["topico"]]
        candidatos_topico = [c for c in conteudos if c.topico_principal in aliases]
        if candidatos_topico:
            conteudos = candidatos_topico

    # Restringe ao tipo de conteúdo pedido (ex.: "atividades sobre X"),
    # senão a busca mistura artigo/vídeo/livro junto com o exercício
    # prático que o aluno pediu de fato
    if intencao["tipo"]:
        candidatos_tipo = [c for c in conteudos if c.tipo == intencao["tipo"]]
        if candidatos_tipo:
            conteudos = candidatos_tipo

    resultados = []
    for conteudo in conteudos:
        vetor_conteudo = bytes_para_embedding(conteudo.embeddings)
        score = calcular_similaridade(embedding_pergunta, vetor_conteudo)
        if score >= threshold:
            resultados.append((conteudo, score))

    resultados.sort(key=lambda x: x[1], reverse=True)
    if not resultados:
        return [], categoria

    # Só mantém resultados próximos do melhor match — evita completar
    # o top_k com conteúdo de outro tópico só porque passou do threshold
    melhor_score = resultados[0][1]
    resultados = [
        (c, s) for c, s in resultados
        if s >= melhor_score - MARGEM_RELEVANCIA
    ]

    return resultados[:top_k], categoria


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

    # 1. Gera o embedding da pergunta (sempre o texto original — ver
    #    buscar_conteudos_relevantes para como o histórico é usado)
    vetor_pergunta = gerar_embedding(pergunta)
    embedding_bytes = vetor_pergunta.tobytes()

    # 2. Busca o pool amplo de candidatos relevantes (mesma pergunta,
    #    mesmo tópico/tipo) com threshold dinâmico via LLM
    candidatos_recomendacao, categoria = buscar_conteudos_relevantes(
        db, vetor_pergunta, pergunta, mensagens
    )
    conteudos_relevantes = candidatos_recomendacao[:TOP_K_CONTEXTO]

    # 3. Monta contexto e histórico
    contexto  = montar_contexto(conteudos_relevantes)
    historico = montar_historico(mensagens)

    return {
        "embedding_pergunta":      embedding_bytes,
        "categoria":               categoria,
        "conteudos_relevantes":    conteudos_relevantes,
        "candidatos_recomendacao": candidatos_recomendacao,
        "contexto":                contexto,
        "historico":               historico,
    }