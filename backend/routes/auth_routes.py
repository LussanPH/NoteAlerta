from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import create_session, token_verification
from sqlalchemy.orm import Session
from typing import Optional
from models import Agente, UBS, Coordenador_Municipal, Vigilancia_Regional, Vigilancia_Estadual
from security import verify_password
from datetime import timedelta, datetime, timezone
from config import ACCESS_TOKEN_EXPIRATE_MINUTES, ALGORITHM, SECRET_KEY
from jose import jwt, JWTError

#Cria o jwt_token para com os dados de id, tipo e data de expiração do token
def create_jwt(id_usuario, tipo, duracao_token = timedelta(minutes=ACCESS_TOKEN_EXPIRATE_MINUTES)):
    data_expiracao = datetime.now(timezone.utc) + duracao_token

    if tipo in ['ACS', 'ACE']:
        tipo = 'ACS/ACE'

    dicionario_informacoes = {"sub": str(id_usuario), "exp": data_expiracao, "tipo": tipo}

    if SECRET_KEY and ALGORITHM:
        jwt_codificado = jwt.encode(dicionario_informacoes, SECRET_KEY, ALGORITHM)

    return jwt_codificado

#Verifica se o login efetuado corresponde a um usuário do banco de dados correspondente ao seu respectivo tipo
def login_auth(cpf, senha, tipo, session:Session):
    if tipo == "ACS/ACE":
        usuario = session.query(Agente).filter(Agente.cpf == cpf).first()
    elif tipo == "UBS":
        usuario = session.query(UBS).filter(UBS.cpf == cpf).first()
    elif tipo == "CM":
        usuario = session.query(Coordenador_Municipal).filter(Coordenador_Municipal.cpf == cpf).first()
    elif tipo == "VR":
        usuario = session.query(Vigilancia_Regional).filter(Vigilancia_Regional.cpf == cpf).first()
    elif tipo == "VE":
        usuario = session.query(Vigilancia_Estadual).filter(Vigilancia_Estadual.cpf == cpf).first()

    else:
        return False

    if not usuario:
        return False
    elif not verify_password(senha, usuario.senha):
        return False
    
    return usuario



auth_router = APIRouter(prefix="/auth", tags=["Autenticação"])


#Endpoint de login do usuário
# Substitua apenas o endpoint @auth_router.post("/login") por este:

@auth_router.post("/login")
async def login(
    dados_login: OAuth2PasswordRequestForm = Depends(),
    tipo_login: Optional[str] = Form(None),
    session: Session = Depends(create_session)
):
    if tipo_login is None:
        tipo_login = dados_login.client_id

    usuario = login_auth(dados_login.username, dados_login.password, tipo_login, session)

    if not usuario:
        raise HTTPException(status_code=400, detail="Usuário não encontrado ou senha inválida.")

    access_token  = create_jwt(usuario.id, tipo_login)
    refresh_token = create_jwt(usuario.id, tipo_login, timedelta(days=1))

    dados_usuario = {
        "id":    usuario.id,
        "nome":  usuario.nome,
        "cpf": usuario.cpf,
    }

    if tipo_login == "ACS/ACE":
        dados_usuario["cargo"] = usuario.cargo
        dados_usuario["microarea"] = usuario.microarea

    elif tipo_login == "CM":
        dados_usuario["cargo"] = "Coordenador Municipal"
        dados_usuario["municipio"] = usuario.municipio

    elif tipo_login == "UBS":
        dados_usuario["ubs"]       = usuario.ubs
        dados_usuario["municipio"] = usuario.municipio

    elif tipo_login == "VR":
        dados_usuario["superintendencia"] = usuario.superintendencia
        dados_usuario["cargo"] = "Vigilante Regional"

    elif tipo_login == "VE":
        dados_usuario["cargo"] = "Vigilante Estadual"

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "type_token":    "Bearer",
        "usuario":       dados_usuario,
    }
    
    
#Endpoint para a criação de um no access_token a partir do refresh_token
@auth_router.post("/refresh")
async def create_access_token(dict_info: dict = Depends(token_verification)):
    tipo = dict_info.get("tipo")
    sub = dict_info.get("sub")

    if tipo in ["ACS/ACE", "UBS", "CM", "VR", "VE"]:
        access_token = create_jwt(sub, tipo)
        return {
            "access_token": access_token,
            "type_token": "Bearer"
        }
    
    raise HTTPException(status_code=400, detail="Tipo de token inválido para renovação.")