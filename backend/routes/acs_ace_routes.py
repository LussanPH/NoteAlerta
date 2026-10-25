from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from dependencies import create_session, token_verification, somente_Agente, get_usuario
from models import Agente, UBS, Notificacao, NotificacaoMedia
from relatorio_xlsx import xlsx_response, relatorio_consolidado, relatorio_notificacao
from filtros import FiltrosRelatorio, filtros_relatorio_periodo
from typing import List, Annotated
from sqlalchemy.orm import Session
from sqlalchemy import select
from security import get_hashed_password
from datetime import datetime, date
from config import GROK_API_KEY, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME
from groq import Groq
import cloudinary
import cloudinary.uploader
import httpx


cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure = True
)


acs_ace_router = APIRouter(prefix="/agentes", tags=["Agentes"], dependencies=[Depends(somente_Agente)])
client = Groq(api_key=GROK_API_KEY)




#Lista as notificações de um agente com base em quem está logado
@acs_ace_router.get("/listar_notificacoes")
async def listar_notificacoes(session : Session = Depends(create_session), usuario = Depends(get_usuario)):
    notificacoes = session.query(Notificacao).filter(Notificacao.acs_ace_id == usuario.id).all()

    return {
        "Notificações" : notificacoes
    }


#Endpoint para transcrição do áudio enviado pelo agente
@acs_ace_router.post("/transcricao_audio")
async def transcricao_audio(audio : UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail='Nenhum áudio encontrado.')
    
    try:
        audio_bytes = await audio.read()

        transcricao = client.audio.transcriptions.create(
            file = (audio.filename, audio_bytes),
            model = "whisper-large-v3",
            response_format='json',
            language='pt'
        )

        return {'texto_transcrito': transcricao.text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro na transcrição: {str(e)}')

async def obter_coordenadas(
    endereco: str,
    municipio: str,
    estado: str
):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{endereco}, {municipio}, {estado}, Brasil",
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": "Sentinela-App/1.0"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers=headers,
        )

    print("ENDEREÇO BUSCADO:", params["q"])
    print("STATUS NOMINATIM:", response.status_code)
    print("RESPOSTA NOMINATIM:", response.json())

    if response.status_code != 200:
        return None, None

    resultados = response.json()

    if not resultados:
        return None, None

    latitude = float(resultados[0]["lat"])
    longitude = float(resultados[0]["lon"])

    return latitude, longitude

#Criação de uma notificação com base no agente que está logado
@acs_ace_router.post("/criar_notificacao")
async def criar_notificacao(
    nome : str = Form(...), 
    tipo_evento : str = Form(...),
    categoria : str = Form(...),
    pessoas_animais_infectados_afetados : int = Form(...),
    local_ocorrencia : str = Form(...),
    endereco : str = Form(None), 
    estado : str = Form(None),
    municipio : str = Form(None), 
    continuidade_situacao : str = Form(...), 
    descricao : str = Form(...),
    medias : list[UploadFile] = File(default=[]),  #RETIRADO STATUS DO FORMULÁRIO
    rascunho : bool = Form(...), 
    data_ocorrencia_str : str = Form(...),
    session : Session = Depends(create_session), 
    usuario = Depends(get_usuario)
):
    data_envio = datetime.now()
    data_ocorrencia = datetime.fromisoformat(str(data_ocorrencia_str))
    latitude = None
    longitude = None

    if endereco and municipio and estado:
        latitude, longitude = await obter_coordenadas(
            endereco,
            municipio,
            estado,
        )

    notificacao_nova = Notificacao(
        nome=nome,
        tipo_evento=tipo_evento,
        categoria=categoria,
        data_envio=data_envio,
        pessoas_animais_infectados_afetados=pessoas_animais_infectados_afetados,
        local_ocorrencia=local_ocorrencia,
        data_ocorrencia=data_ocorrencia,

        estado=estado,
        municipio=municipio,
        endereco=endereco,

        latitude=latitude,
        longitude=longitude,

        continuidade_situacao=continuidade_situacao,
        descricao=descricao,
        acs_ace_id=usuario.id,
        status="PENDENTE",             #CAMPO STATUS COMO PENDENTE POR PADRÃO
        rascunho=rascunho,
        verificada=False              #ADICONADO O CAMPO VALIDADO COMO FALSE
    )
    
    session.add(notificacao_nova)
    session.flush()
    
    for media in medias:
            if media.filename:
                try:
                    resultado = cloudinary.uploader.upload(media.file)
    
                    url_final = resultado.get("secure_url")
    
                    media_nova = NotificacaoMedia(
                        url = url_final,
                        notificacao_id = notificacao_nova.id
                    )

                    session.add(media_nova)
    
                except Exception as e:
                    session.rollback()
                    return {"Erro":f"Falha ao enviar imagem {media.filename}: {str(e)}"}
                
    session.commit()

    return {"response": f"Notificação {notificacao_nova.nome} criada com sucesso!"}



@acs_ace_router.get("/exportar_relatorio")
async def exportar_relatorio(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        notificacoes = session.query(Notificacao).filter(
            Notificacao.acs_ace_id == usuario.id,
        ).all()
        
        relatorio = [
            {
                "id": n.id,
                "categoria": getattr(n, 'categoria', 'N/A'),
                "tipo": getattr(n, 'tipo_evento', 'N/A'),
                "status": n.status,
                "data": getattr(n, 'data_ocorrencia', 'N/A'),
                "local": getattr(n, 'local_ocorrencia', 'N/A')
            }
            for n in notificacoes
        ]
        
        return {"relatorio": relatorio, "nome_agente": usuario.nome, 'cpf_agente': usuario.cpf, 'usuario_microarea' : usuario.microarea}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@acs_ace_router.get("/exportar_relatorio/xlsx")
async def exportar_relatorio_xlsx(
    filtros: FiltrosRelatorio = Depends(filtros_relatorio_periodo),
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = (
            session.query(Notificacao)
            .filter(
                Notificacao.acs_ace_id == usuario.id,
                *filtros.condicoes()
            )
            .order_by(Notificacao.data_ocorrencia.desc())
            .all()
        )

        wb = relatorio_consolidado(
            {"Agente": usuario.nome, "CPF": usuario.cpf, "Microárea": usuario.microarea, **filtros.resumo(session, notificacoes)},
            notificacoes
        )

        return xlsx_response(wb, f"relatorio_{usuario.nome}.xlsx")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar XLSX: {str(e)}"
        )
        
@acs_ace_router.get("/notificacoes/{notificacao_id}/relatorio_xlsx")
async def gerar_relatorio_notificacao_xlsx(
    notificacao_id: int,
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacao = session.scalars(
            select(Notificacao)
            .where(Notificacao.acs_ace_id == usuario.id,
                  Notificacao.id == notificacao_id)
        ).first()

        if not notificacao:
            raise HTTPException(
                status_code=404,
                detail="Notificação não encontrada."
            )

        return xlsx_response(
            relatorio_notificacao(notificacao),
            f"notificacao_{notificacao.id}_{notificacao.municipio}.xlsx"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


