from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from dependencies import create_session, get_usuario, somente_VE
from security import get_hashed_password
from models import Notificacao, Vigilancia_Estadual, Vigilancia_Regional, COADS, Superintendencias_Ceara, Municipios, Agente, Dados_UBS
from relatorio_xlsx import xlsx_response, relatorio_consolidado, relatorio_notificacao
from filtros import FiltrosRelatorio, filtros_relatorio
from schemas import VigilanteEstadualSchema, VigilanteRegionalSchema, Notificacao_com_Coads_e_Superintendencia, NotificacaoSchema



ve_router = APIRouter(prefix="/ve", tags=['ve'], dependencies=[Depends(somente_VE)])




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

@ve_router.get("/exportar_relatorio/xlsx")
async def exportar_relatorio_xlsx(
    filtros: FiltrosRelatorio = Depends(filtros_relatorio),
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
            .where(*filtros.condicoes())
            .order_by(Notificacao.data_ocorrencia.desc())
        ).all()
        
        
        wb = relatorio_consolidado(
            {"Vigilante": usuario.nome, **filtros.resumo(session, notificacoes)},
            notificacoes,
            colunas_extras=("COADS", "Superintendência")
        )

        return xlsx_response(wb, f"relatorio_{usuario.nome}.xlsx")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar XLSX: {str(e)}"
        )
        
@ve_router.get("/notificacoes/{notificacao_id}/relatorio_xlsx")
async def gerar_relatorio_notificacao_xlsx(
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
    