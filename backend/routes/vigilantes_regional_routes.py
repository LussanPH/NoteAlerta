from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from dependencies import create_session, get_usuario, somente_VR
from security import get_hashed_password
from models import Notificacao, Vigilancia_Regional, Superintendencias_Ceara, Coordenador_Municipal, Municipios, COADS
from schemas import VigilanteRegionalSchema, CMSchema, Notificacao_com_Coads, NotificacaoSchema
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



vr_router = APIRouter(prefix='/vr', tags=['vr'], dependencies=[Depends(somente_VR)])


def celula(valor : str, style : ParagraphStyle):
    return Paragraph(escape(valor), style)


#Criação de conta CM
@vr_router.post("/criar_conta_coordenador")
async def criar_cm(cm_schema : CMSchema, session : Session = Depends(create_session)): 
    cm = session.query(Coordenador_Municipal).filter(Coordenador_Municipal.cpf == cm_schema.cpf).first()

    if cm:
        raise HTTPException(status_code=400, detail="Coordenador já cadastrado no sistema!")
    
    senha_hashed = get_hashed_password(cm_schema.senha)
    cm_novo = Coordenador_Municipal(cm_schema.cpf, senha_hashed, cm_schema.nome, cm_schema.municipio)
    session.add(cm_novo)
    session.commit()
    
    return {"message": "Coordenador Municipal criado com sucesso!"}



@vr_router.get('/notificacoes', response_model=list[Notificacao_com_Coads])
async def listar_notificacoes(  
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session),
):

    notificacoes_coads = session.execute(
        select(Notificacao, COADS.coads)
        .join(Municipios, Notificacao.municipio == Municipios.municipio)
        .join(COADS, Municipios.fk_coads == COADS.id)
        .where(COADS.fk_superintendencia == usuario.superintendencia)
    ).all()

    return [
        Notificacao_com_Coads(
            **NotificacaoSchema.model_validate(row.Notificacao).model_dump(),
            coads = row.coads
        )

        for row in notificacoes_coads
    ]
    

@vr_router.get('/dados_superintendencia_coads')
async def dados_superintendencia(usuario = Depends(get_usuario), session : Session = Depends(create_session)):
    try:
        dados_superintendencia = session.execute(
            select(Superintendencias_Ceara, COADS.coads)
            .join(COADS, Superintendencias_Ceara.id == COADS.fk_superintendencia)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).all()
        
        if not dados_superintendencia:
            raise HTTPException(status_code=400, detail='Superintendência do usuário não encontrada.')
        
        return [
            {
                "Superintendencia":dados.nome,
                "COADS":coads
            }

            for dados, coads in dados_superintendencia
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro ao tentar encontrar dados da superintendência: {e}')



@vr_router.get("/exportar_relatorio")
async def exportar_relatorio(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).all()
        
        dados_superintendencia = session.scalars(
            select(Superintendencias_Ceara)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).first()
        
        if not dados_superintendencia:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à superintendência com id: {usuario.ubs}")
        
        relatorio = [
            {
                "id": n.id,
                "categoria": getattr(n, 'categoria', 'N/A'),
                "tipo": getattr(n, 'tipo_evento', 'N/A'),
                "status": n.status,
                "data": getattr(n, 'data_ocorrencia', 'N/A'),
                "local": getattr(n, 'local_ocorrencia', 'N/A'),
                "coads": coads,
            }
            for n, coads in notificacoes
        ]
        
        return {"relatorio": relatorio, "superintendencia": dados_superintendencia.nome}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@vr_router.get("/exportar_relatorio/pdf")
async def exportar_relatorio_pdf(
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).all()
              
        dados_superintendencia = session.scalars(
            select(Superintendencias_Ceara)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).first()
              
        if not dados_superintendencia:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à superintendência com id: {usuario.ubs}")

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
                f"Superintendência: {dados_superintendencia.nome}",
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
            "COADS"
        ]]
        
        row_style = ParagraphStyle(
            "Célula",
            parent=styles['Normal'],
            fontSize=8,
            leading = 10
        )
        

        for n, coads in notificacoes:
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
                celula(str(coads), row_style)
            ])

        tabela = Table(
            dados,
            repeatRows=1,
            colWidths=[25, 150, 60, 80, 100, 80, 60],
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
                    f'attachment; filename="relatorio_{dados_superintendencia.nome}.pdf"'
                )
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar PDF: {str(e)}"
        )
        
@vr_router.get("/notificacoes/{notificacao_id}/relatorio_pdf")
async def gerar_relatorio_notificacao_pdf(
    notificacao_id: int,
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacao = session.scalars(
            select(Notificacao)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .where(Superintendencias_Ceara.id == usuario.superintendencia, Notificacao.id == notificacao_id)
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
