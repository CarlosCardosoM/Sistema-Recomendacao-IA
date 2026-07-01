import token

from sqlalchemy import DateTime, Float, ForeignKey, LargeBinary, create_engine, Column, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

#criando o banco
db = create_engine("sqlite:///banco.db")

#criando a base
Base = declarative_base() 

#classes da tabela do banco
# Aluno
class Aluno(Base):
    __tablename__ = "alunos"
    id = Column("id",Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String, nullable=False)
    email = Column("email",String, nullable=False)
    token = Column("token",             String,   nullable=True)
    token_expira_em = Column("token_expira_em",   DateTime, nullable=True)
    preferencias_tipos = Column("preferencias_tipos", String, nullable=True)

    #Relacionamentos
    interacoes = relationship("Interacao", backref="aluno")
    curtidas = relationship("Curtida", backref="aluno")
    sessoes = relationship("Sessao", backref="aluno")
    
    def __init__(self, nome, email, token=None, token_expira_em=None, preferencias_tipos=None):
        self.nome = nome
        self.email = email
        self.token = token
        self.token_expira_em = token_expira_em
        self.preferencias_tipos = preferencias_tipos

# Conteúdo
class Conteudo(Base):
    __tablename__ = "conteudos"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    titulo = Column("titulo", String, nullable=False)
    tipo = Column("tipo", String, nullable=False)
    descricao = Column("descricao", String, nullable=False)
    link = Column("link", String, nullable=False)
    idioma = Column("idioma", String, nullable=False)
    topico_principal = Column("topico_principal", String, nullable=False)
    subtopicos = Column("subtopicos", String, nullable=False)
    palavras_chave = Column("palavras_chave", String, nullable=False)
    nivel_dificuldade = Column("nivel_dificuldade", String, nullable=False)
    embeddings = Column("embeddings", LargeBinary, nullable=True)

    #Relacionamentos
    interacoes = relationship("Interacao", backref="conteudo")
    curtidas = relationship("Curtida", backref="conteudo")
    chunk_usages = relationship("ChunkUsage", backref="conteudo")

    def __init__(self, titulo, tipo, descricao, link, idioma, topico_principal, subtopicos, palavras_chave, nivel_dificuldade, embeddings):
        self.titulo = titulo
        self.tipo = tipo
        self.descricao = descricao
        self.link = link
        self.idioma = idioma
        self.topico_principal = topico_principal
        self.subtopicos = subtopicos
        self.palavras_chave = palavras_chave
        self.nivel_dificuldade = nivel_dificuldade
        self.embeddings = embeddings

# Interação
class Interacao(Base):
    __tablename__ = "interacoes"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    aluno_id = Column ("id_aluno", ForeignKey("alunos.id"))
    conteudo_id = Column("id_conteudo", ForeignKey("conteudos.id"))
    tempo_visualizacao = Column("tempo_visualizacao", Float, nullable=True)
    aberto_em = Column("aberto_em", DateTime, nullable=False)
    fechado_em = Column("fechado_em", DateTime, nullable=True)


    def __init__(self, aluno_id, conteudo_id, tempo_visualizacao=None, aberto_em=None, fechado_em=None):
        self.aluno_id = aluno_id
        self.conteudo_id = conteudo_id
        self.tempo_visualizacao = tempo_visualizacao
        self.aberto_em = aberto_em
        self.fechado_em = fechado_em

# Curtida
class Curtida(Base):
    __tablename__ = "curtidas"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    aluno_id = Column("id_aluno", ForeignKey("alunos.id"))
    conteudo_id = Column("id_conteudo", ForeignKey("conteudos.id"))

    def __init__(self, aluno_id, conteudo_id):
        self.aluno_id = aluno_id
        self.conteudo_id = conteudo_id
# Sessao
class Sessao(Base):
    __tablename__ = "sessoes"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    aluno_id = Column("id_aluno", ForeignKey("alunos.id"))
    data_hora_inicio = Column("data_hora_inicio", DateTime, nullable=False, server_default=func.now())
    data_hora_fim = Column("data_hora_fim", DateTime, nullable=True)

    #Relacionamentos
    mensagens = relationship("Mensagem", backref="sessao")

    
    def __init__(self, aluno_id, data_hora_inicio=None, data_hora_fim=None):
        self.aluno_id = aluno_id
        self.data_hora_inicio = data_hora_inicio
        self.data_hora_fim = data_hora_fim 
# Mensagem
class Mensagem(Base):
    __tablename__ = "mensagens"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    sessao_id = Column("id_sessao", ForeignKey("sessoes.id"), nullable=False)
    papel = Column("papel", String, nullable=False)
    conteudo = Column("conteudo", String, nullable=False)
    analise_pergunta = Column("analise_pergunta", String, nullable=True)
    embedding_pergunta = Column("embedding_pergunta", LargeBinary, nullable=True)
    criado_em = Column("criado_em", DateTime, server_default=func.now())
    
    #Relacionamentos
    chunk_usages = relationship("ChunkUsage", backref="mensagem")

    def __init__(self, sessao_id, papel, conteudo, analise_pergunta, embedding_pergunta):
        self.sessao_id = sessao_id
        self.papel = papel
        self.conteudo = conteudo
        self.analise_pergunta = analise_pergunta
        self.embedding_pergunta = embedding_pergunta

class ChunkUsage(Base):
    __tablename__ = "chunk_usage"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    mensagem_id = Column("id_mensagem", ForeignKey("mensagens.id"), nullable=False)
    conteudo_id = Column("id_conteudo", ForeignKey("conteudos.id"), nullable=False)
    similaridade_score = Column("similaridade", Float, nullable=False)


    def __init__(self, mensagem_id, conteudo_id, similaridade_score):
        self.mensagem_id = mensagem_id
        self.conteudo_id = conteudo_id
        self.similaridade_score = similaridade_score

Base.metadata.create_all(db)

print("Banco de dados criado com sucesso!")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db)

def get_db():
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()



 

