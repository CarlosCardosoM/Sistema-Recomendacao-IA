from fastapi import FastAPI
from views.curtida_router import router as curtida_router
from views.interacao_router import router as interacao_router
from views.aluno_router import router as aluno_router
from views.chat_router import router as chat_router

app = FastAPI(
    title="Sistema de Recomendação de Conteúdo",
    description="Chatbot educacional com RAG para alunos de Sistemas de Informação",
    version="1.0.0"
)

app.include_router(aluno_router)
app.include_router(chat_router)
app.include_router(interacao_router)
app.include_router(curtida_router)