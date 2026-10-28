from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from dependencies import create_session, get_usuario, somente_VR
from security import get_hashed_password
from models import Notificacao, Vigilancia_Regional, Superintendencias_Ceara, Coordenador_Municipal, Municipios, COADS
from relatorio_xlsx import xlsx_response, relatorio_consolidado, relatorio_notificacao
from filtros import FiltrosRelatorio, filtros_relatorio
from schemas import VigilanteRegionalSchema, CMSchema, Notificacao_com_Coads, NotificacaoSchema




vr_router = APIRouter(prefix='/vr', tags=['vr'], dependencies=[Depends(somente_VR)])




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

@vr_router.get("/exportar_relatorio/xlsx")
async def exportar_relatorio_xlsx(
    filtros: FiltrosRelatorio = Depends(filtros_relatorio),
    usuario=Depends(get_usuario),
    session: Session = Depends(create_session)
):
    try:
        notificacoes = session.execute(
            select(Notificacao, COADS.coads)
            .join(Municipios, Notificacao.municipio == Municipios.municipio)
            .join(COADS, Municipios.fk_coads == COADS.id)
            .join(Superintendencias_Ceara, COADS.fk_superintendencia == Superintendencias_Ceara.id)
            .where(Superintendencias_Ceara.id == usuario.superintendencia, *filtros.condicoes())
        ).all()
              
        dados_superintendencia = session.scalars(
            select(Superintendencias_Ceara)
            .where(Superintendencias_Ceara.id == usuario.superintendencia)
        ).first()
              
        if not dados_superintendencia:
            raise HTTPException(status_code=404, detail=f"Nenhuma notificação encontada atrelada à superintendência com id: {usuario.ubs}")

        wb = relatorio_consolidado(
            {"Superintendência": dados_superintendencia.nome, **filtros.resumo(session, notificacoes)},
            notificacoes,
            colunas_extras=("COADS",)
        )

        return xlsx_response(wb, f"relatorio_{dados_superintendencia.nome}.xlsx")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar XLSX: {str(e)}"
        )
        
@vr_router.get("/notificacoes/{notificacao_id}/relatorio_xlsx")
async def gerar_relatorio_notificacao_xlsx(
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
