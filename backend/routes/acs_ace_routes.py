from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from dependencies import create_session, token_verification, somente_Agente, get_usuario
from models import Agente, UBS, Notificacao, NotificacaoMedia
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
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure = True
)


acs_ace_router = APIRouter(prefix="/agentes", tags=["Agentes"], dependencies=[Depends(somente_Agente)])
client = Groq(api_key=GROK_API_KEY)


def celula(valor : str, style : ParagraphStyle):
    return Paragraph(escape(valor), style)


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

@acs_ace_router.get("/exportar_relatorio/pdf")
async def exportar_relatorio_pdf(
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = (
            session.query(Notificacao)
            .filter(
                Notificacao.acs_ace_id == usuario.id,
            )
            .order_by(Notificacao.data_ocorrencia.desc())
            .all()
        )

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        elementos = []

        titulo = styles["Title"]
        titulo.alignment = TA_CENTER

        elementos.append(
            Paragraph(
                "Relatório de Notificações",
                titulo
            )
        )

        elementos.append(Spacer(1, 12))

        elementos.append(
            Paragraph(
                f"Agente: {usuario.nome}",
                styles["Normal"]
            )
        )
        
        elementos.append(
            Paragraph(
                f"CPF: {usuario.cpf}",
                styles["Normal"]
            )
        )
        
        elementos.append(
            Paragraph(
                f"Microárea: {usuario.microarea}",
                styles["Normal"]
            )
        )

        elementos.append(
            Paragraph(
                f"Total de notificações: {len(notificacoes)}",
                styles["Normal"]
            )
        )

        elementos.append(Spacer(1, 20))

        dados : list[list[str | Paragraph]] = [[
            "ID",
            "Categoria",
            "Evento",
            "Status",
            "Local",
            "Data"
        ]]
        
        row_style = ParagraphStyle(
            "Célula",
            parent=styles['Normal'],
            fontSize=8,
            leading = 10
        )
        

        for n in notificacoes:
            data = '-'
            if n.data_ocorrencia.strftime("%d/%m/%Y %H:%M"):
                data = n.data_ocorrencia.strftime("%d/%m/%Y %H:%M") 
            dados.append([
                celula(str(n.id), row_style),
                celula(str(n.categoria or '-'), row_style),
                celula(str(n.tipo_evento or '-'), row_style),
                celula(str(n.status), row_style),
                celula(str(n.local_ocorrencia) or '-', row_style),
                celula(str(data), row_style)
            ])

        tabela = Table(
            dados,
            repeatRows=1,
            colWidths=[25, 150, 60, 80, 100, 80],
        )

        tabela.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0F6E56")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F5F8F7")
                    ]
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ])
        )

        elementos.append(tabela)

        doc.build(elementos)

        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="relatorio_{usuario.nome}.pdf"'
                )
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar PDF: {str(e)}"
        )
        
@acs_ace_router.get("/notificacoes/{notificacao_id}/relatorio_pdf")
async def gerar_relatorio_notificacao_pdf(
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

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        titulo = styles["Title"]
        titulo.alignment = TA_CENTER

        elementos = []

        elementos.append(
            Paragraph(
                "Relatório da Notificação",
                titulo
            )
        )

        elementos.append(Spacer(1, 20))

        dados = [
            ["Protocolo", f"#{str(notificacao.id).zfill(7)}"],
            ["Município", str(notificacao.municipio or "—")],
            ["Tipo do evento", str(notificacao.tipo_evento or "—")],
            ["Categoria", str(notificacao.categoria or "—")],
            ["Status", str(notificacao.status or "—")],
            ["Data de Ocorência", str(notificacao.data_ocorrencia or "—")],
            ["Local", str(notificacao.local_ocorrencia or "—")],
            [
                "Afetados",
                str(
                    notificacao.pessoas_animais_infectados_afetados
                    or 0
                )
            ],
            [
                "Continuidade da situação",
                str(notificacao.continuidade_situacao or "—")
            ],
        ]

        tabela = Table(
            dados,
            colWidths=[160, 320]
        )

        tabela.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ])
        )

        elementos.append(tabela)

        elementos.append(Spacer(1, 20))

        elementos.append(
            Paragraph(
                "<b>Descrição</b>",
                styles["Heading2"]
            )
        )

        elementos.append(Spacer(1, 8))

        descricao = (
            notificacao.descricao
            or "Nenhuma descrição informada."
        )

        # Quebra linhas da descrição
        descricao = descricao.replace("\n", "<br/>")

        elementos.append(
            Paragraph(
                descricao,
                styles["BodyText"]
            )
        )

        doc.build(elementos)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        nome_arquivo = (
            f"notificacao_{notificacao.id}_"
            f"{notificacao.municipio}.pdf"
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{nome_arquivo}"'
                )
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


