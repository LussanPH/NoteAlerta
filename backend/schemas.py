from pydantic import BaseModel
from typing import Optional, List
from fastapi import UploadFile
import datetime

#Schema dos Agentes ACS/ACE
class AgenteSchema(BaseModel):
    senha : str
    cargo : str
    nome : str
    ubs_atuante : int
    cpf : str
    microarea : str

    class Config:
        from_attributes = True

#Schema da conta UBS
class UBSSchema(BaseModel):
    senha : str
    ubs : int
    nome : str
    municipio : str
    cpf : str
    
    class Config:
        from_attributes = True

#Schema das notificações a serem postadas pelos agentes acs/ace
class NotificacaoSchema(BaseModel):
    id: int
    nome : str
    tipo_evento : str
    categoria : str
    data_envio : datetime.datetime
    data_ocorrencia : datetime.datetime
    pessoas_animais_infectados_afetados : int
    local_ocorrencia : str
    estado : str
    municipio : str
    endereco : str | None
    latitude : float | None
    longitude : float | None
    continuidade_situacao : str
    descricao : str
    acs_ace_id : int
    status : str
    rascunho : bool
    verificada : bool
    
    class Config:
        from_attributes = True

#Schema dos dados de uma UBS
class DadosUBSSchema(BaseModel):
    nome: str
    municipio: str
    estado: str

    class Config:
        from_attributes = True


#Schema dos dados do Coordenador Municipal
class CMSchema(BaseModel):
    nome: str
    cpf: str
    senha: str
    municipio: str

    class Config:
        from_attributes = True


#Schema dos dados do Vigilante Regional
class VigilanteRegionalSchema(BaseModel):
    nome: str
    cpf: str
    senha: str
    superintendencia: int

    class Config:
        from_attributes = True


#Schema dos dados do Vigilante Estadual

class VigilanteEstadualSchema(BaseModel):
    nome: str
    cpf: str
    senha: str

    class Config:
        from_attributes = True   


# Schema de Saída de uma Notificação para Vigilante Regional

class Notificacao_com_Coads(BaseModel):
    id: int
    nome : str
    tipo_evento : str
    categoria : str
    data_envio : datetime.datetime
    data_ocorrencia : datetime.datetime
    pessoas_animais_infectados_afetados : int
    local_ocorrencia : str
    estado : str
    municipio : str
    endereco : str | None
    latitude : float | None
    longitude : float | None
    continuidade_situacao : str
    descricao : str
    acs_ace_id : int
    status : str
    rascunho : bool
    verificada : bool
    coads : str
    
    class Config:
        from_attributes = True   


class Notificacao_com_Coads_e_Superintendencia(BaseModel):
    id: int
    nome : str
    tipo_evento : str
    categoria : str
    data_envio : datetime.datetime
    data_ocorrencia : datetime.datetime
    pessoas_animais_infectados_afetados : int
    local_ocorrencia : str
    estado : str
    municipio : str
    endereco : str | None
    latitude : float | None
    longitude : float | None
    continuidade_situacao : str
    descricao : str
    acs_ace_id : int
    status : str
    rascunho : bool
    verificada : bool
    coads : str
    superintendencia: str
    
    class Config:
        from_attributes = True


class Notificacao_com_Dados_UBS(BaseModel):
    id: int
    nome : str
    tipo_evento : str
    categoria : str
    data_envio : datetime.datetime
    data_ocorrencia : datetime.datetime
    pessoas_animais_infectados_afetados : int
    local_ocorrencia : str
    estado : str
    municipio : str
    endereco : str | None
    latitude : float | None
    longitude : float | None
    continuidade_situacao : str
    descricao : str
    acs_ace_id : int
    status : str
    rascunho : bool
    verificada : bool
    nome_ubs : str
    
    class Config:
        from_attributes = True
    