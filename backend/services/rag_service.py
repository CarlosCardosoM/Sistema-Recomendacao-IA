import numpy as np
from sqlalchemy.orm import Session

from database import Conteudo
from services.embedding_service import (
    gerar_embedding,
    bytes_para_embedding
)
from services.ollama_service import analisar_intencao

TOP_K = 3

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
    # Uma única chamada ao LLM decide: é técnica (threshold baixo) ou
    # genérica (threshold alto)? aponta pra um tópico específico? pede um
    # tipo de conteúdo específico (ex.: atividade)? Sempre a pergunta crua,
    # sem concatenar com o histórico: misturar texto (ex.: "Boa noite" +
    # "Busca cega") dilui o sinal e derruba a classificação. O histórico
    # recente entra como turnos separados só pra resolver referências
    # ("esse algoritmo") sem se confundir com saudações irrelevantes.
    historico_recente = None
    if mensagens:
        historico_recente = [
            {"role": m.papel, "content": m.conteudo} for m in mensagens[-4:]
        ]

    intencao = (
        analisar_intencao(pergunta, list(TOPICOS_ALIASES.keys()), TIPOS_DISPONIVEIS, historico_recente)
        if pergunta else {"tecnica": False, "topico": None, "tipo": None}
    )
    eh_tecnica = intencao["tecnica"]
    threshold = THRESHOLD_TECNICO if eh_tecnica else THRESHOLD_GENERICO

    conteudos = db.query(Conteudo).filter(Conteudo.embeddings != None).all()

    # Restringe ao tópico identificado, quando a pergunta apontar
    # claramente para um — evita que o embedding "vaze" pra um subtópico
    # vizinho só porque a similaridade textual é parecida.
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
        return []

    # Só mantém resultados próximos do melhor match — evita completar
    # o top_k com conteúdo de outro tópico só porque passou do threshold
    melhor_score = resultados[0][1]
    resultados = [
        (c, s) for c, s in resultados
        if s >= melhor_score - MARGEM_RELEVANCIA
    ]

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
    # 1. Gera o embedding da pergunta (sempre o texto original — ver
    #    buscar_conteudos_relevantes para como o histórico é usado)
    vetor_pergunta = gerar_embedding(pergunta)
    embedding_bytes = vetor_pergunta.tobytes()

    # 2. Busca conteúdos com threshold dinâmico via LLM
    conteudos_relevantes = buscar_conteudos_relevantes(
        db, vetor_pergunta, pergunta, mensagens
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