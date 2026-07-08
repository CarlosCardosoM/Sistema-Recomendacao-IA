import unicodedata
from sqlalchemy.orm import Session

from database import Aluno, Conteudo, Interacao, Curtida

# ── Pesos do scoreFinal ───────────────────────────────────────────────────────
# Similaridade semântica domina — garante que o conteúdo seja relevante
# para a pergunta antes de considerar preferências e histórico do aluno
PESO_SIMILARIDADE = 0.60  # ← aumentado de 0.35 para 0.60
PESO_PREFERENCIA  = 0.15  # tipo de conteúdo preferido pelo aluno
PESO_CURTIDA      = 0.08  # já curtiu esse conteúdo
PESO_HISTORICO    = 0.05  # já interagiu com esse conteúdo antes
PESO_TEMPO        = 0.04  # tempo de visualização normalizado
PESO_INTERACAO    = 0.03  # engajamento geral com o sistema
PESO_DIFICULDADE  = 0.05  # nível compatível com a pergunta

TEMPO_REFERENCIA = 300  # 5 minutos
SCORE_MINIMO_RECOMENDACAO = 0.30
TOP_K_RECOMENDACOES = 3  # quantidade sempre buscada, desde a 1ª pergunta do aluno


def normalizar_texto(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto_sem_acento = unicodedata.normalize("NFKD", texto)
    texto_sem_acento = "".join(
        c for c in texto_sem_acento if not unicodedata.combining(c)
    )
    return texto_sem_acento.lower().strip()


# O cadastro guarda a preferência com o rótulo do frontend ("Exercício"),
# mas o catálogo de conteúdo usa "atividade" em Conteudo.tipo — sem esse
# alias, a preferência por exercícios nunca batia com nada e o peso de
# preferência ficava sempre zerado
ALIAS_TIPO_PREFERENCIA = {
    "exercicio": "atividade",
}


def _tipo_normalizado(tipo: str) -> str:
    tipo_norm = normalizar_texto(tipo)
    return ALIAS_TIPO_PREFERENCIA.get(tipo_norm, tipo_norm)


def _combina_com_preferencia(conteudo: Conteudo, aluno: Aluno) -> bool:
    if not aluno.preferencias_tipos:
        return False
    preferencias = {_tipo_normalizado(t) for t in aluno.preferencias_tipos.split(",")}
    return normalizar_texto(conteudo.tipo) in preferencias


def _tipos_preferidos_normalizados(aluno: Aluno) -> list[str]:
    if not aluno.preferencias_tipos:
        return []
    tipos = []
    for t in aluno.preferencias_tipos.split(","):
        tipo = _tipo_normalizado(t)
        if tipo and tipo not in tipos:
            tipos.append(tipo)
    return tipos


def normalizar_tempo(tempo_segundos: float | None) -> float:
    if tempo_segundos is None:
        return 0.0
    return min(tempo_segundos / TEMPO_REFERENCIA, 1.0)


def calcular_score(
    db: Session,
    aluno: Aluno,
    conteudo: Conteudo,
    score_similaridade: float,
    nivel_pergunta: str | None
) -> float:
    # 1. Similaridade semântica — fator dominante (já calculada pelo RAG)

    # 2. Preferência de tipo de conteúdo
    score_preferencia = 1.0 if _combina_com_preferencia(conteudo, aluno) else 0.0

    # 3. Curtida
    curtida = db.query(Curtida).filter(
        Curtida.aluno_id == aluno.id,
        Curtida.conteudo_id == conteudo.id
    ).first()
    score_curtida = 1.0 if curtida else 0.0

    # 4. Histórico de interação
    interacao_existente = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id,
        Interacao.conteudo_id == conteudo.id
    ).first()
    score_historico = 0.5 if interacao_existente else 0.0

    # 5. Tempo de visualização
    score_tempo = 0.0
    if interacao_existente:
        score_tempo = normalizar_tempo(interacao_existente.tempo_visualizacao)

    # 6. Engajamento geral
    quantidade_abertos = db.query(Interacao).filter(
        Interacao.aluno_id == aluno.id
    ).count()
    score_interacao = min(quantidade_abertos * 0.1, 1.0)

    # 7. Compatibilidade de dificuldade
    score_dificuldade = 0.0
    if nivel_pergunta and normalizar_texto(nivel_pergunta) == normalizar_texto(conteudo.nivel_dificuldade):
        score_dificuldade = 1.0

    score_final = (
        PESO_SIMILARIDADE * score_similaridade +
        PESO_PREFERENCIA  * score_preferencia  +
        PESO_CURTIDA      * score_curtida       +
        PESO_HISTORICO    * score_historico     +
        PESO_TEMPO        * score_tempo         +
        PESO_INTERACAO    * score_interacao     +
        PESO_DIFICULDADE  * score_dificuldade
    )
    return score_final


def _selecionar_com_preferencia_e_diversidade(
    elegiveis: list[tuple[Conteudo, float]],
    aluno: Aluno
) -> list[tuple[Conteudo, float]]:
    """
    Monta a lista final de recomendações a partir dos candidatos elegíveis
    (já ordenados por score, do melhor pro pior).

    O peso de preferência no score (PESO_PREFERENCIA) sozinho não garante
    que o tipo preferido do aluno apareça: se a similaridade semântica de
    outros tipos for maior, o vídeo preferido pode nunca entrar no top-3.
    Por isso a seleção é feita em duas etapas:
      1. Reserva a(s) primeira(s) vaga(s) pro melhor conteúdo elegível de
         cada tipo que o aluno marcou como preferência no cadastro.
      2. Preenche o restante priorizando tipos ainda não presentes na
         lista (diversidade de mídia), e só repete tipo se não houver
         mais opção elegível de um tipo novo.
    """
    tipos_preferidos = _tipos_preferidos_normalizados(aluno)
    selecionados: list[tuple[Conteudo, float]] = []
    ids_selecionados: set[int] = set()

    for tipo_pref in tipos_preferidos:
        if len(selecionados) >= TOP_K_RECOMENDACOES:
            break
        melhor = next(
            (
                item for item in elegiveis
                if item[0].id not in ids_selecionados
                and _tipo_normalizado(item[0].tipo) == tipo_pref
            ),
            None
        )
        if melhor:
            selecionados.append(melhor)
            ids_selecionados.add(melhor[0].id)

    tipos_presentes = {_tipo_normalizado(c.tipo) for c, _ in selecionados}
    for conteudo, score in elegiveis:
        if len(selecionados) >= TOP_K_RECOMENDACOES:
            break
        if conteudo.id in ids_selecionados or _tipo_normalizado(conteudo.tipo) in tipos_presentes:
            continue
        selecionados.append((conteudo, score))
        ids_selecionados.add(conteudo.id)
        tipos_presentes.add(_tipo_normalizado(conteudo.tipo))

    for conteudo, score in elegiveis:
        if len(selecionados) >= TOP_K_RECOMENDACOES:
            break
        if conteudo.id in ids_selecionados:
            continue
        selecionados.append((conteudo, score))
        ids_selecionados.add(conteudo.id)

    return selecionados


def recomendar_conteudo(
    db: Session,
    email: str,
    conteudos_relevantes: list[tuple[Conteudo, float]],
    nivel_pergunta: str | None = None
) -> list[dict]:
    aluno = db.query(Aluno).filter(Aluno.email == email).first()
    if not aluno:
        return []

    # Personaliza apenas entre os conteúdos que o RAG já considerou
    # semanticamente relevantes para a pergunta — nunca busca fora desse
    # conjunto, para que preferência/curtida/histórico não puxem uma
    # recomendação para um tópico diferente do que foi perguntado.
    lista_scores = []
    for conteudo, score_similaridade in conteudos_relevantes:
        score = calcular_score(db, aluno, conteudo, score_similaridade, nivel_pergunta)
        lista_scores.append((conteudo, score))

    # Ordena por score: relevância pra pergunta primeiro (0.60, dominante),
    # preferência de tipo em seguida (0.15) desempata entre conteúdos já
    # comparáveis em relevância. Funciona de verdade porque
    # conteudos_relevantes agora chega com um pool mais amplo de candidatos
    # (ver rag_service.TOP_K_CANDIDATOS) — antes só os 3 melhores por
    # similaridade bruta chegavam aqui, e se nenhum fosse do tipo preferido
    # do aluno não havia o que escolher. A ordenação por score sozinha ainda
    # não garante que o tipo preferido apareça (ver
    # _selecionar_com_preferencia_e_diversidade), só define a prioridade
    # dentro de cada etapa da seleção.
    lista_scores.sort(key=lambda x: x[1], reverse=True)

    # Só o que passou do score mínimo entra na disputa pelas vagas
    elegiveis = [(c, s) for c, s in lista_scores if s >= SCORE_MINIMO_RECOMENDACAO]

    top_recomendacoes = _selecionar_com_preferencia_e_diversidade(elegiveis, aluno)

    return [
        {
            "conteudo_id": conteudo.id,
            "titulo":      conteudo.titulo,
            "tipo":        conteudo.tipo,
            "link":        conteudo.link,
            "score":       round(score, 3)
        }
        for conteudo, score in top_recomendacoes
    ]