from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, MetaData, JSON, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from config import DATABASE_URL


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

convention = {
    "ix": "ix_%(column_0_label)s",                                 
    "uq": "uq_%(table_name)s_%(column_0_name)s",                        
    "ck": "ck_%(table_name)s_%(constraint_name)s",                      
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", 
    "pk": "pk_%(table_name)s"                                           
}

metadata = MetaData(naming_convention=convention)

db = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, echo=True)
Base = declarative_base(metadata=metadata)

class Agente(Base):
    __tablename__ = "Agentes"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    senha = Column("senha", String)
    cargo = Column("cargo", String)
    nome = Column("nome", String)
    ubs_atuante = Column("ubs_atuante", ForeignKey("Dados_UBS.id"))
    microarea = Column("microarea", String)
    cpf = Column("cpf", String)

    def __init__(self, senha, cargo, nome, ubs_atuante, cpf, microarea):
        self.senha = senha
        self.cargo = cargo
        self.nome = nome
        self.ubs_atuante = ubs_atuante
        self.cpf = cpf
        self.microarea = microarea


class UBS(Base): 
    __tablename__ = "UBS"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    senha = Column("senha", String)
    nome = Column("nome", String)
    ubs = Column("ubs", ForeignKey("Dados_UBS.id"))
    municipio = Column("municipio", ForeignKey("Dados_UBS.municipio"))
    cpf = Column("cpf", String)

    def __init__(self, senha, nome, ubs, municipio, cpf):
        self.senha = senha
        self.nome = nome
        self.ubs = ubs
        self.municipio = municipio
        self.cpf = cpf


class Coordenador_Municipal(Base):
    __tablename__ = "Coordenadores"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    cpf = Column("cpf", String)
    senha = Column("senha", String)
    nome = Column("nome", String)
    municipio = Column("municipio", String)

    def __init__(self, cpf, senha, nome, municipio):
        self.cpf = cpf
        self.senha = senha
        self.nome = nome
        self.municipio = municipio


class Notificacao(Base):
    __tablename__ = "Notificaçoes"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String)
    tipo_evento = Column("tipo_evento", String)
    categoria = Column("categoria", String)
    data_envio = Column("data_envio", DateTime)
    data_ocorrencia = Column("data_ocorrencia", DateTime)
    pessoas_animais_infectados_afetados = Column("pessoas_animais_infectados_afetados", Integer)
    local_ocorrencia = Column("local_ocorrencia", String)
    estado = Column("estado", String, nullable=True)
    municipio = Column("municipio", String, nullable=True)
    endereco = Column("endereco", String, nullable=True) 
    latitude = Column("latitude", Float, nullable=True)
    longitude = Column("longitude", Float, nullable=True)
    
    continuidade_situacao = Column("continuidade_situacao", String)
    descricao = Column("descricao", String)
    media_urls = relationship("NotificacaoMedia", back_populates="notificacao")
    acs_ace_id = Column("acs_ace_id", ForeignKey("Agentes.id"))
    status = Column("status", String)
    rascunho = Column("rascunho", Boolean)
    verificada = Column("verificada", Boolean)

    def __init__(
        self,
        nome,
        tipo_evento,
        categoria,
        data_envio,
        pessoas_animais_infectados_afetados,
        local_ocorrencia,
        continuidade_situacao,
        descricao,
        acs_ace_id,
        data_ocorrencia,
        status="PENDENTE",
        verificada = False,          
        rascunho=True,
        estado=None,
        municipio=None,
        endereco=None,
        latitude=None,
        longitude=None
    ):
        self.nome = nome
        self.tipo_evento = tipo_evento
        self.categoria = categoria
        self.data_envio = data_envio
        self.data_ocorrencia = data_ocorrencia
        self.pessoas_animais_infectados_afetados = pessoas_animais_infectados_afetados
        self.local_ocorrencia = local_ocorrencia

        self.estado = estado
        self.municipio = municipio
        self.endereco = endereco

        self.latitude = latitude
        self.longitude = longitude

        self.continuidade_situacao = continuidade_situacao
        self.descricao = descricao
        self.acs_ace_id = acs_ace_id
        self.status = status
        self.rascunho = rascunho
        self.verificada = verificada           


class NotificacaoMedia(Base):
    __tablename__ = "Notificacoes_Media"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    url = Column("url", String)
    notificacao_id = Column("notificacao_id", ForeignKey("Notificaçoes.id"))

    notificacao = relationship("Notificacao", back_populates="media_urls")

    def __init__(self, url, notificacao_id):
        self.url = url
        self.notificacao_id = notificacao_id


class Dados_UBS(Base):
    __tablename__ = "Dados_UBS"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String, nullable=False)
    municipio = Column("municipio", String, nullable=False)
    estado = Column("estado", String, nullable=False)

    def __init__(self, nome, municipio, estado):
        self.nome = nome
        self.municipio = municipio
        self.estado = estado



class Superintendencias_Ceara(Base):
    __tablename__ = "Superintendencias_Ceara"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String, nullable=False)



class COADS(Base):
    __tablename__ = 'COADS'

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    coads = Column("coads", String, nullable=False)
    fk_superintendencia = Column("fk_superintendencia", ForeignKey("Superintendencias_Ceara.id"))



class Municipios(Base):
    __tablename__ = 'Municipios'

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    municipio = Column("municipio", String, nullable=False)
    fk_coads = Column("fk_coads", ForeignKey("COADS.id"))
    


class Vigilancia_Regional(Base):
    __tablename__ = "Vigilantes_Regional"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    cpf = Column("cpf", String)
    senha = Column("senha", String)
    nome = Column("nome", String, nullable=False)
    superintendencia = Column("superintendencia", ForeignKey("Superintendencias_Ceara.id"))

    def __init__(self, cpf, senha, nome, superintendencia):
        self.cpf = cpf
        self.senha = senha
        self.nome = nome
        self.superintendencia = superintendencia


class Vigilancia_Estadual(Base):
    __tablename__ = "Vigilantes_Estadual"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    cpf = Column("cpf", String)
    senha = Column("senha", String)
    nome = Column("nome", String, nullable=False)

    def __init__(self, cpf, senha, nome):
        self.cpf = cpf
        self.senha = senha
        self.nome = nome



