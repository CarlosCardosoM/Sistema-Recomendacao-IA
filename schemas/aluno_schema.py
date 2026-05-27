from pydantic import BaseModel


class AlunoCriar(BaseModel):
    nome: str
    email: str
    senha: str
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

class AlunoAtualizarSenha(BaseModel):
    senha_atual: str
    nova_senha: str

class AlunoAtualizarPreferencias(BaseModel):
    preferencias_tipos: str        