from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from dependencies import create_session, somente_CM, get_usuario
from security import get_hashed_password
from models import Notificacao, Coordenador_Municipal, UBS, Agente, Dados_UBS
from relatorio_xlsx import xlsx_response, relatorio_consolidado, relatorio_notificacao
from filtros import FiltrosRelatorio, filtros_relatorio
from schemas import CMSchema, UBSSchema, AgenteSchema, Notificacao_com_Dados_UBS, NotificacaoSchema


cm_router = APIRouter(prefix="/cm", tags=["cm"], dependencies=[Depends(somente_CM)])




#Criação de conta Agente ACS/ACE
@cm_router.post("/criar_conta_acs_ace")
async def criar_acs_ace(acs_ace_schema : AgenteSchema, session : Session = Depends(create_session)): 
    acs_ace = session.query(Agente).filter(Agente.cpf == acs_ace_schema.cpf).first()

    if acs_ace:
        raise HTTPException(status_code=400, detail="Agente já cadastrado no sistema!")
    
    senha_hashed = get_hashed_password(acs_ace_schema.senha)
    acs_ace_novo = Agente(senha_hashed, acs_ace_schema.cargo, acs_ace_schema.nome, acs_ace_schema.ubs_atuante, acs_ace_schema.cpf, acs_ace_schema.microarea)
    session.add(acs_ace_novo)
    session.commit()
    
    return {"message": "Agente criado com sucesso!"}



#Criaçaõ de conta UBS
@cm_router.post("/criar_conta_ubs")
async def criar_ubs(ubs_schema : UBSSchema, session : Session = Depends(create_session)): 
    ubs = session.query(UBS).filter(UBS.cpf == ubs_schema.cpf).first()

    if ubs:
        raise HTTPException(status_code=400, detail="Conta UBS já cadastrada no sistema!")
    
    senha_hashed = get_hashed_password(ubs_schema.senha)
    ubs_novo = UBS(senha_hashed, ubs_schema.nome, ubs_schema.ubs, ubs_schema.municipio, ubs_schema.cpf)
    session.add(ubs_novo)
    session.commit()
    
    return {"message": "Conta UBS criada com sucesso!"}



#Lista notificações da região
@cm_router.get("/listar_notificacoes")
async def listar_notificacoes_ubs(usuario = Depends(get_usuario), session : Session = Depends(create_session)):
    try:
        notificacoes = session.execute(
            select(Notificacao, Dados_UBS)
            .join(Agente, Notificacao.acs_ace_id == Agente.id)
            .join(Dados_UBS, Agente.ubs_atuante == Dados_UBS.id)
            .where(Notificacao.municipio == usuario.municipio)
        ).all()

        return{
            "Notificacao": [
                    Notificacao_com_Dados_UBS(
                        **NotificacaoSchema.model_validate(notificacao).model_dump(),
                        nome_ubs= dado_ubs.nome
                    )
                
                
                for notificacao, dado_ubs in notificacoes
                ],
            "Quantidade": len(notificacoes)
        }
        
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar notificações: {str(e)}")


#Alteração dos status de uma notificação

@cm_router.patch("/notificacoes/{notificacao_id}/status_em_investigacao")
async def status_em_investigacao(notificacao_id: int, usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "EM INVESTIGAÇÃO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@cm_router.patch("/notificacoes/{notificacao_id}/status_veridico")
async def status_veridico(notificacao_id: int, usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "VERÍDICO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@cm_router.patch("/notificacoes/{notificacao_id}/status_nao_veridico")
async def status_descartado(notificacao_id: int, usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "NÃO VERÍDICO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@cm_router.patch("/notificacoes/{notificacao_id}/status_encerrado")
async def status_encerrado(notificacao_id: int, usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notificacao.status = "ENCERRADO"
    session.commit()

    return {"status_code": 200, "id_notificacao":notificacao_id, "status_notificacao":notificacao.status}


@cm_router.patch("/notificacoes/{notificacao_id}/complementar")
async def complementar_notificacao(notificacao_id: int, informacao_extra: str, usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    notificacao = session.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    
    notificacao.descricao += f"\n[Complemento Coordenador]: {informacao_extra}"
    session.commit()
    return {"message": "Notificação complementada com sucesso!"}


@cm_router.delete("/notificacoes/{notificacao_id}/deletar")
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


# Métricas resumidas do município
@cm_router.get("/dashboard_stats")
async def obter_estatisticas(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        total = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio).count()
        investigacao = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio, Notificacao.status == "EM INVESTIGAÇÃO").count()
        veridicos = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio, Notificacao.status == "VERÍDICO").count()
        nao_veridico = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio, Notificacao.status == "NÃO VERÍDICO").count()
        encerrado = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio, Notificacao.status == "ENCERRADO").count()
        pendente = session.query(Notificacao).filter(Notificacao.municipio == usuario.municipio, Notificacao.status == "PENDENTE").count()
        
        return {
            "total": total,
            "em_investigacao": investigacao,
            "veridicos": veridicos,
            "nao_veridicos": nao_veridico,
            "encerrados": encerrado,
            "pendentes": pendente
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar estatísticas: {str(e)}")

@cm_router.get("/exportar_relatorio")
async def exportar_relatorio(usuario = Depends(get_usuario), session: Session = Depends(create_session)):
    try:
        notificacoes = session.query(Notificacao).filter(
            Notificacao.municipio == usuario.municipio,
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
        
        return {"relatorio": relatorio, "municipio": usuario.municipio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@cm_router.get("/exportar_relatorio/xlsx")
async def exportar_relatorio_xlsx(
    filtros: FiltrosRelatorio = Depends(filtros_relatorio),
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = (
            session.query(Notificacao)
            .filter(
                Notificacao.municipio == usuario.municipio,
                *filtros.condicoes()
            )
            .order_by(Notificacao.data_ocorrencia.desc())
            .all()
        )

        wb = relatorio_consolidado(
            {"Município": usuario.municipio, **filtros.resumo(session, notificacoes)},
            notificacoes
        )

        return xlsx_response(wb, f"relatorio_{usuario.municipio}.xlsx")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar XLSX: {str(e)}"
        )
        
@cm_router.get("/notificacoes/{notificacao_id}/relatorio_xlsx")
async def gerar_relatorio_notificacao_xlsx(
    notificacao_id: int,
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacao = session.scalars(
            select(Notificacao)
            .where(Notificacao.municipio == usuario.municipio,
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