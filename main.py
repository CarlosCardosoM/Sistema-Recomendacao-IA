from fastapi import FastAPI
from views.aluno_router import router as aluno_router

app = FastAPI()
app.include_router(aluno_router)