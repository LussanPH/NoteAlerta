from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from dependencies import create_session, somente_UBS, get_usuario
from security import get_hashed_password
from models import Notificacao, UBS, Agente, Dados_UBS
from schemas import NotificacaoSchema, UBSSchema, AgenteSchema
import datetime
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

ubs_router = APIRouter(prefix="/ubs", tags=["ubs"], dependencies=[Depends(somente_UBS)])


def celula(valor : str, style : ParagraphStyle):
    return Paragraph(escape(valor), style)


#Criação de conta acs/ace
@ubs_router.post("/criar_conta_acs_ace")
async def criar_acs_ace(agente_schema : AgenteSchema, session : Session = Depends(create_session)): 
    acs_ace = session.query(Agente).filter(Agente.cpf == agente_schema.cpf).first()

    if acs_ace:
        raise HTTPException(status_code=400, detail="UBS já cadastrada no sistema!")
    
    senha_hashed = get_hashed_password(agente_schema.senha)
    acs_ace_novo = Agente(senha_hashed, agente_schema.cargo, agente_schema.nome, agente_schema.ubs_atuante, agente_schema.cpf, agente_schema.microarea)
    session.add(acs_ace_novo)
    session.commit()
    
    return {"message": f"Conta agente {acs_ace_novo.cargo} criada com sucesso!"}


# Listar notificações associadas aos agentes da UBS logada
@ubs_router.get("/notificacoes")
async def listar_notificacoes_ubs(
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        resultados = (
            session.query(Notificacao, Agente)
            .join(
                Agente,
                Notificacao.acs_ace_id == Agente.id
            )
            .filter(
                Agente.ubs_atuante == usuario.ubs,
                Notificacao.rascunho == False
            )
            .all()
        )

        notificacoes = []

        for notificacao, agente in resultados:
            notificacoes.append({
                "id": notificacao.id,
                "nome": notificacao.nome,
                "tipo_evento": notificacao.tipo_evento,
                "categoria": notificacao.categoria,
                "data_ocorrencia": notificacao.data_ocorrencia,
                "data_envio": notificacao.data_envio,
                "pessoas_animais_infectados_afetados":
                    notificacao.pessoas_animais_infectados_afetados,
                "local_ocorrencia": notificacao.local_ocorrencia,
                "continuidade_situacao": notificacao.continuidade_situacao,
                "descricao": notificacao.descricao,
                "acs_ace_id": notificacao.acs_ace_id,
                "acs_ace_nome": agente.nome,
                "acs_ace_microarea": agente.microarea,
                "status": notificacao.status,
                "rascunho": notificacao.rascunho,
            })

        return {"notificacoes": notificacoes}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar notificações: {str(e)}"
        )


#Valida Notificação
@ubs_router.patch("/notificacoes/{notificacao_id}/validar")
async def validar_notificacao(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.verificada = True
    session.commit()

    return {"message":f"Notificação {notificacao_id} verificada com sucesso!"}


# Complementar Notificação
@ubs_router.patch("/notificacoes/{notificacao_id}/complementar")
async def complementar_notificacao(notificacao_id: int, informacao_extra: str, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    
    notificacao.descricao += f"\n[Complemento UBS]: {informacao_extra}"
    session.commit()
    return {"message": "Notificação complementada com sucesso!"}


#Rota para retornar o nome da ubs no qual o usuário logado pertence
@ubs_router.get("/dados_ubs")
async def dados_da_ubs(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    dados_ubs = session.query(Dados_UBS).filter(Dados_UBS.id == usuario.ubs).first()  
    if not dados_ubs:
        raise HTTPException(status_code=404, detail="Dados da UBS não cadastrados no sistema.")
    
    return {"Dados da UBS": dados_ubs}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_em_investigacao")
async def status_em_investigacao(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "EM INVESTIGAÇÃO"
    session.commit()

    return {"message":f"Status da notificação {notificacao_id}: Em investigação!"}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_veridico")
async def status_veridico(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "VERÍDICO"
    session.commit()

    return {"message":f"Status da notificação {notificacao_id}: Verídico!"}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_nao_veridico")
async def status_descartado(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "NÃO VERÍDICO"
    session.commit()

    return {"message":f"Status da notificação {notificacao_id}: Não Verídico!"}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_encerrado")
async def status_encerrado(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "ENCERRADO"
    session.commit()

    return {"message":f"Status da notificação {notificacao_id}: Encerrado!"}



@ubs_router.get("/exportar_relatorio")
async def exportar_relatorio(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        notificacoes_dados_ubs = session.scalars(
            select(Notificacao)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .where(Dados_UBS.id == usuario.ubs)
        ).all()
        
        dados_ubs = session.scalars(
            select(Dados_UBS)
            .where(Dados_UBS.id == usuario.ubs)
        ).first()
        
        if not dados_ubs:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à ubs de id: {usuario.ubs}")
        
        relatorio = [
            {
                "id": n.id,
                "categoria": getattr(n, 'categoria', 'N/A'),
                "tipo": getattr(n, 'tipo_evento', 'N/A'),
                "status": n.status,
                "data": getattr(n, 'data_ocorrencia', 'N/A'),
                "local": getattr(n, 'local_ocorrencia', 'N/A')
            }
            for n in notificacoes_dados_ubs
        ]
        
        return {"relatorio": relatorio, "UBS": dados_ubs.nome, "Municipio": dados_ubs.municipio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@ubs_router.get("/exportar_relatorio/pdf")
async def exportar_relatorio_pdf(
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = session.scalars(
            select(Notificacao)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .where(Dados_UBS.id == usuario.ubs)
            .order_by(Notificacao.data_ocorrencia.desc())
        ).all()
        
        
        dados_ubs = session.scalars(
            select(Dados_UBS)
            .where(Dados_UBS.id == usuario.ubs)
        ).first()
        
        if not dados_ubs:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à ubs de id: {usuario.ubs}")

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
                f"Município: {dados_ubs.municipio}",
                styles["Normal"]
            )
        )
        
        elementos.append(
            Paragraph(
                f"UBS: {dados_ubs.nome}",
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
                    f'attachment; filename="relatorio_{usuario.municipio}.pdf"'
                )
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar PDF: {str(e)}"
        )
        
@ubs_router.get("/notificacoes/{notificacao_id}/relatorio_pdf")
async def gerar_relatorio_notificacao_pdf(
    notificacao_id: int,
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacao = session.scalars(
            select(Notificacao)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .where(Dados_UBS.id == usuario.ubs, Notificacao.id == notificacao_id)
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

