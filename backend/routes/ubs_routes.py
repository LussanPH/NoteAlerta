from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from dependencies import create_session, somente_UBS, get_usuario
from security import get_hashed_password
from models import Notificacao, UBS, Agente, Dados_UBS
from relatorio_xlsx import xlsx_response, relatorio_consolidado, relatorio_notificacao
from filtros import FiltrosRelatorio, filtros_relatorio
from schemas import NotificacaoSchema, UBSSchema, AgenteSchema
import datetime


ubs_router = APIRouter(prefix="/ubs", tags=["ubs"], dependencies=[Depends(somente_UBS)])




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

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_veridico")
async def status_veridico(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "VERÍDICO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_nao_veridico")
async def status_descartado(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "NÃO VERÍDICO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@ubs_router.patch("/notificacoes/{notificacao_id}/status_encerrado")
async def status_encerrado(notificacao_id: int, session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "ENCERRADO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}



@ubs_router.delete("/notificacoes/{notificacao_id}/deletar")
async def deletar_notificacao(notificacao_id : int, session : Session = Depends(create_session)):
    notificacao = session.scalars(
        select(Notificacao)
        .where(Notificacao.id == notificacao_id)
    ).first()
    
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    session.delete(notificacao)
    session.commit()
    
    return {"status_code": 200, "id_notificacao":notificacao_id, "message":f"Notificação {notificacao.id} excluída com sucesso"}



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

@ubs_router.get("/exportar_relatorio/xlsx")
async def exportar_relatorio_xlsx(
    filtros: FiltrosRelatorio = Depends(filtros_relatorio),
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = session.scalars(
            select(Notificacao)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .where(Dados_UBS.id == usuario.ubs, *filtros.condicoes())
            .order_by(Notificacao.data_ocorrencia.desc())
        ).all()
        
        
        dados_ubs = session.scalars(
            select(Dados_UBS)
            .where(Dados_UBS.id == usuario.ubs)
        ).first()
        
        if not dados_ubs:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à ubs de id: {usuario.ubs}")

        wb = relatorio_consolidado(
            {"Município": dados_ubs.municipio, "UBS": dados_ubs.nome, **filtros.resumo(session, notificacoes)},
            notificacoes
        )

        return xlsx_response(wb, f"relatorio_{usuario.municipio}.xlsx")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar XLSX: {str(e)}"
        )
        
@ubs_router.get("/notificacoes/{notificacao_id}/relatorio_xlsx")
async def gerar_relatorio_notificacao_xlsx(
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

