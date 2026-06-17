from fastapi import FastAPI
from views.aluno_router import router as aluno_router
from views.chat_router import router as chat_router

app = FastAPI(
    title="Sistema de Recomendação de Conteúdo",
    description="Chatbot educacional com RAG para alunos de Sistemas de Informação",
    version="1.0.0"
)

app.include_router(aluno_router)
app.include_router(chat_router)