import json
import numpy as np
import requests
from sqlalchemy.orm import sessionmaker
from database import Conteudo, db

ARQUIVO_JSON     = "conteudos.json"
OLLAMA_URL = "http://localhost:11434/api/embed"
MODELO_EMBEDDING = "nomic-embed-text"

SessionLocal = sessionmaker(bind=db)


def gerar_embedding(texto: str) -> bytes:
    response = requests.post(OLLAMA_URL, json={
        "model":  MODELO_EMBEDDING,
        "input": texto 
    })
    response.raise_for_status()
    vetor = response.json()["embeddings"][0]
    return np.array(vetor, dtype=np.float32).tobytes()


def indexar_conteudos():
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        conteudos = json.load(f)

    sessao = SessionLocal()

    print(f" {len(conteudos)} conteúdos encontrados\n")

    for i, item in enumerate(conteudos, start=1):
        # Verifica se já existe pelo link — evita duplicatas
        existente = sessao.query(Conteudo).filter(Conteudo.link == item["link"]).first()
        if existente:
            print(f"[{i}]  Já existe: {item['titulo']}")
            continue

        print(f"[{i}]  Gerando embedding: {item['titulo']}")

        # Monta o texto para embedding
        # igual ao gerarEmbeddingConteudo() do pseudocódigo
        texto = " ".join([
            item.get("titulo", ""),
            item.get("descricao", ""),
            item.get("topico_principal", ""),
            item.get("palavras_chave", ""),
        ])

        embedding = gerar_embedding(texto)

        conteudo = Conteudo(
            titulo            = item["titulo"],
            tipo              = item["tipo"],
            descricao         = item["descricao"],
            link              = item["link"],
            idioma            = item["idioma"],
            topico_principal  = item["topico_principal"],
            subtopicos        = item.get("subtopicos", ""),
            palavras_chave    = item.get("palavras_chave", ""),
            nivel_dificuldade = item["nivel_dificuldade"],
            embeddings        = embedding
        )
        sessao.add(conteudo)
        sessao.commit()
        print(f"[{i}] ✅ Salvo: {item['titulo']}\n")

    sessao.close()
    print("Indexação concluída!")


if __name__ == "__main__":
    indexar_conteudos()