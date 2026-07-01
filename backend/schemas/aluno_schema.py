from pydantic import BaseModel


class AlunoCriar(BaseModel):
    nome: str
    email: str
    preferencias_tipos: str | None = None

class AlunoResposta(BaseModel):
    id: int
    nome: str
    email: str
    preferencias_tipos: str | None    

    class Config:
        from_attributes = True

class AlunoAtualizarEmail(BaseModel):
    novo_email: str

class AlunoVerificarToken(BaseModel):
    email: str
    token: str

class AlunoAtualizarPreferencias(BaseModel):
    preferencias_tipos: str

class AlunoLogin(BaseModel):
    email: str