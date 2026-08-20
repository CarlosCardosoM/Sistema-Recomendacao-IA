# Sabiá — Sistema de Recomendação de Conteúdo com IA

Chatbot educacional com RAG (Retrieval-Augmented Generation) para alunos de Sistemas de Informação, com foco em Algoritmos de Busca.
## Sumário

- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [1. Clonar o repositório](#1-clonar-o-repositório)
- [2. Configurar o backend](#2-configurar-o-backend)
- [3. Configurar o Ollama](#3-configurar-o-ollama)
- [4. Variáveis de ambiente](#4-variáveis-de-ambiente)
- [5. Criar o banco de dados](#5-criar-o-banco-de-dados)
- [6. Indexar o catálogo de conteúdos](#6-indexar-o-catálogo-de-conteúdos)
- [7. Rodar o backend](#7-rodar-o-backend)
- [8. Configurar e rodar o frontend](#8-configurar-e-rodar-o-frontend)
- [Endpoints da API](#endpoints-da-api)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Solução de problemas](#solução-de-problemas)

## Arquitetura

```
Aluno (frontend React)
        │
        ▼
FastAPI (backend/main.py)
        │
        ├─ Classificação de intenção  → modelo "llama3.2" (Ollama)
        │  (tecnica / saudação / fora_do_escopo)
        │
        ├─ Busca semântica de conteúdo → embeddings "nomic-embed-text"
        │  comparados com os embeddings do catálogo (SQLite)
        │
        ├─ Geração da resposta        → modelo "chatbootIA" (Ollama)
        │  (llama3.2 + persona definida no Modelfile)
        │
        └─ Recomendação de conteúdo   → score combinando similaridade,
           preferências, curtidas, histórico e nível de dificuldade
```

O backend é um projeto **FastAPI + SQLAlchemy** (SQLite) e o frontend é uma SPA em **React + Vite**. Todo o processamento de linguagem natural roda localmente através do **Ollama** — não há chamadas a APIs externas de LLM.

## Pré-requisitos

Instale as ferramentas abaixo antes de começar:

| Ferramenta | Versão usada no projeto |
|---|---|
| [Python](https://www.python.org/downloads/) | 3.13 |
| [Node.js](https://nodejs.org/) | 18 |
| [Git](https://git-scm.com/) | qualquer versão recente |
| [Ollama](https://ollama.com/) | qualquer versão recente |

## 1. Clonar o repositório

```bash
git clone https://github.com/CarlosCardosoM/Sistema-Recomendacao-IA.git
cd Sistema-Recomendacao-IA
```

## 2. Configurar o backend

```bash
cd backend
python -m venv venv
```

Ative o ambiente virtual:

```powershell
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## 3. Configurar o Ollama

Com o Ollama instalado e em execução, baixe o modelo de embeddings e o modelo base de chat:

```bash
ollama pull nomic-embed-text
ollama run llama3.2
```

O comando `ollama run llama3.2` baixa o modelo (se ainda não existir) e abre um chat interativo — pode encerrar com `/bye` depois de confirmar que baixou.

Depois, crie o modelo customizado do chatbot a partir do `Modelfile` do projeto (define a persona e os parâmetros de geração, como `temperature`):

```bash
ollama create chatbootIA -f "Ollama LLM.modelfile"
```

> Sempre que o `Ollama LLM.modelfile` for alterado, é preciso rodar `ollama create chatbootIA -f "Ollama LLM.modelfile"` novamente para que a mudança tenha efeito — o backend não lê esse arquivo em tempo de execução, apenas chama o modelo `chatbootIA` já registrado no Ollama.

Confirme que os modelos foram criados:

```bash
ollama list
```

## 4. Variáveis de ambiente

Dentro de `backend/`, crie um arquivo `.env` com as credenciais de envio de e-mail (usadas para o fluxo de cadastro/login por token):

```env
EMAIL_REMETENTE=seu_email@gmail.com
EMAIL_SENHA_APP=sua_senha_de_app
```

> `EMAIL_SENHA_APP` é uma **senha de app**, não a senha normal da conta de e-mail (por exemplo, no Gmail é gerada em Conta Google → Segurança → Senhas de app).

## 5. Criar o banco de dados

Ainda dentro de `backend/`, com o venv ativado:

```bash
python database.py
```

Isso cria o arquivo `banco.db` (SQLite) na raiz de `backend/` com todas as tabelas do sistema (alunos, conteúdos, sessões, mensagens, interações, curtidas, etc.).

## 6. Indexar o catálogo de conteúdos

Com o Ollama rodando e o modelo `nomic-embed-text` já baixado, gere os embeddings dos conteúdos cadastrados em `conteudos.json` e salve-os no banco:

```bash
python indexar_conteudos.py
```

O script pula conteúdos já indexados (identificados por título + tópico principal), então pode ser rodado novamente com segurança sempre que novos itens forem adicionados ao `conteudos.json`.

## 7. Rodar o backend

```bash
uvicorn main:app --reload
```

A API sobe por padrão em `http://localhost:8000`. A documentação interativa (Swagger) fica disponível em `http://localhost:8000/docs`.

## 8. Configurar e rodar o frontend

Em outro terminal, a partir da raiz do projeto:

```bash
cd frontend
npm install
npm run dev
```

O frontend sobe por padrão em `http://localhost:5173` (endereço já liberado no CORS do backend).

## Endpoints da API

Prefixo base: `http://localhost:8000`

| Recurso | Prefixo | Principais rotas |
|---|---|---|
| Alunos | `/alunos` | cadastro, login por token, verificação, edição de e-mail/preferências, exclusão |
| Chat | `/chat` | criar/encerrar/excluir sessão, enviar pergunta (`/sessao/{id}/perguntar`), histórico |
| Curtidas | `/curtidas` | curtir, descurtir, listar, verificar curtida em um conteúdo |
| Interações | `/interacoes` | abrir/fechar interação com um conteúdo, listar, contagem |

Para a lista completa de rotas, parâmetros e schemas, consulte `http://localhost:8000/docs` com o backend em execução.

## Estrutura do projeto

```
Sistema-Recomendacao-IA/
├── backend/
│   ├── controllers/          # Regras de negócio por recurso
│   ├── views/                # Rotas FastAPI (routers)
│   ├── services/
│   │   ├── ollama_service.py     # Chamadas ao Ollama (classificação + geração)
│   │   ├── rag_service.py        # Orquestração do RAG (intenção, busca, contexto)
│   │   ├── embedding_service.py  # Geração de embeddings
│   │   ├── recomendacao_service.py # Score e seleção das recomendações
│   │   └── email_service.py      # Envio de e-mail (login/cadastro por token)
│   ├── schemas/               # Schemas Pydantic (request/response)
│   ├── database.py            # Modelos SQLAlchemy + criação do banco
│   ├── indexar_conteudos.py   # Script de indexação do catálogo
│   ├── conteudos.json         # Catálogo de conteúdos recomendáveis
│   ├── "Ollama LLM.modelfile" # Definição da persona do chatbot (chatbootIA)
│   ├── requirements.txt
│   └── main.py                 # Ponto de entrada da API (FastAPI)
└── frontend/
    ├── src/                    # Aplicação React
    ├── public/
    └── package.json
```

## Solução de problemas

**O chatbot recusa perguntas técnicas válidas (ex.: sobre BFS, DFS, A\*, minimax).**
Verifique se os modelos `llama3.2` e `chatbootIA` estão instalados (`ollama list`) e se o Ollama está rodando na porta padrão (`11434`). A classificação de intenção roda em `llama3.2` puro antes de chegar no `chatbootIA` — se o Ollama não estiver acessível, a chamada falha silenciosamente e a pergunta pode ser tratada como fora do escopo.

**Erro de CORS no frontend.**
Confirme que o frontend está rodando em `http://localhost:5173` — é o único endpoint liberado em `app.add_middleware(CORSMiddleware, ...)` no `main.py`. Se mudar a porta do Vite, ajuste essa lista no backend.

**Nenhum conteúdo é recomendado.**
Confirme que `python indexar_conteudos.py` foi executado com sucesso e que `nomic-embed-text` está baixado no Ollama. Sem embeddings salvos no banco, a busca semântica não tem o que comparar.

**E-mail de login/cadastro não chega.**
Confira `EMAIL_REMETENTE` e `EMAIL_SENHA_APP` no `.env` — a segunda precisa ser uma senha de app, não a senha da conta.
