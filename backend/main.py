from fastapi import FastAPI
from views.curtida_router import router as curtida_router
from views.interacao_router import router as interacao_router
from views.aluno_router import router as aluno_router
from views.chat_router import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema de Recomendação de Conteúdo",
    description="Chatbot educacional com RAG para alunos de Sistemas de Informação",
    version="1.0.0"
)

app.include_router(aluno_router)
app.include_router(chat_router)
app.include_router(interacao_router)
app.include_router(curtida_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)