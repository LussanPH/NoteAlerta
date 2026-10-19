from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from dependencies import create_session, get_usuario, somente_VE
from security import get_hashed_password
from models import Notificacao, Vigilancia_Estadual, Vigilancia_Regional, COADS, Superintendencias_Ceara, Municipios, Agente, Dados_UBS
from schemas import VigilanteEstadualSchema, VigilanteRegionalSchema, Notificacao_com_Coads_e_Superintendencia, NotificacaoSchema
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


ve_router = APIRouter(prefix="/ve", tags=['ve'], dependencies=[Depends(somente_VE)])


def celula(valor : str, style : ParagraphStyle):
    return Paragraph(escape(valor), style)


@ve_router.post('/criar_conta_ve')
async def criar_ve(ve_schema : VigilanteEstadualSchema, session : Session = Depends(create_session)):
    ve = session.query(Vigilancia_Estadual).filter(Vigilancia_Estadual.cpf == ve_schema.cpf).first()

    if ve:
        raise HTTPException(status_code=400, detail='Vigilante Estadual já existente no sistema!')

    senha_hashed = get_hashed_password(ve_schema.senha)
    ve_novo = Vigilancia_Estadual(ve_schema.cpf, senha_hashed, ve_schema.nome)
    session.add(ve_novo)
    session.commit()

    return {'message' : 'Vigilante Estadual criado com sucesso!'}



@ve_router.post('/criar_conta_vr')
async def criar_vr(vr_schema : VigilanteRegionalSchema, session : Session = Depends(create_session)):
    vr = session.query(Vigilancia_Regional).filter(Vigilancia_Regional.cpf == vr_schema.cpf).first()

    if vr:
        raise HTTPException(status_code=400, detail="Vigilante Regional já cadastrado no sistema!")

    senha_hashed = get_hashed_password(vr_schema.senha)
    vr_novo = Vigilancia_Regional(vr_schema.cpf, senha_hashed, vr_schema.nome, vr_schema.superintendencia)
    session.add(vr_novo)
    session.commit()

    return {'message': 'Vigilante Regional cadastrado com sucesso!'}



@ve_router.get('/notificacoes')
async def listar_notificacoes(session : Session = Depends(create_session)):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads, Superintendencias_Ceara.nome)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
        ).all()

        return{
            "Notificações" : [
                Notificacao_com_Coads_e_Superintendencia(
                    **NotificacaoSchema.model_validate(row.Notificacao).model_dump(),
                    coads = row.coads,
                    superintendencia =  row.nome
                )
                for row in notificacoes
                ],
            "Quantidade" : len(notificacoes)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao retornar notificações: {e}")
    
    
@ve_router.get("/exportar_relatorio")
async def exportar_relatorio(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads, Superintendencias_Ceara.nome)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
        ).all()
        
        relatorio = [
            {
                "id": n.id,
                "categoria": getattr(n, 'categoria', 'N/A'),
                "tipo": getattr(n, 'tipo_evento', 'N/A'),
                "status": n.status,
                "data": getattr(n, 'data_ocorrencia', 'N/A'),
                "local": getattr(n, 'local_ocorrencia', 'N/A'),
                "coads": coads,
                "superintendencia": superintendencia,
            }
            for n, coads, superintendencia in notificacoes
        ]
        
        return {"relatorio": relatorio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@ve_router.get("/exportar_relatorio/pdf")
async def exportar_relatorio_pdf(
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads, Superintendencias_Ceara.nome)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .order_by(Notificacao.data_ocorrencia.desc())
        ).all()
        
        
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
                f"Vigilante Regional: {usuario.nome}",
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
            "Data",
            "COADS",
            "Superintendencia"
        ]]
        
        row_style = ParagraphStyle(
            "Célula",
            parent=styles['Normal'],
            fontSize=8,
            leading = 10
        )
        

        for n, coads, superintendencia in notificacoes:
            data = '-'
            if n.data_ocorrencia.strftime("%d/%m/%Y %H:%M"):
                data = n.data_ocorrencia.strftime("%d/%m/%Y %H:%M") 
            dados.append([
                celula(str(n.id), row_style),
                celula(str(n.categoria or '-'), row_style),
                celula(str(n.tipo_evento or '-'), row_style),
                celula(str(n.status), row_style),
                celula(str(n.local_ocorrencia) or '-', row_style),
                celula(str(data), row_style),
                celula(str(coads), row_style),
                celula(str(superintendencia), row_style)
            ])

        tabela = Table(
            dados,
            repeatRows=1,
            colWidths=[25, 100, 60, 50, 100, 60, 50, 70],
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
        
@ve_router.get("/notificacoes/{notificacao_id}/relatorio_pdf")
async def gerar_relatorio_notificacao_pdf(
    notificacao_id: int,
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacao = session.query(Notificacao).filter(
            Notificacao.id == notificacao_id,
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
    