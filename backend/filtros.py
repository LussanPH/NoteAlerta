from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from models import Notificacao, Agente


@dataclass
class FiltrosRelatorio:
    data_inicio: date | None = None
    data_fim: date | None = None
    agente_id: int | None = None

    # Condições para .where(); lista vazia (sem filtros) não altera a query
    def condicoes(self) -> list:
        condicoes = []

        if self.data_inicio:
            condicoes.append(Notificacao.data_ocorrencia >= datetime.combine(self.data_inicio, time.min))
        if self.data_fim:
            # data_ocorrencia é DateTime: o limite é o início do dia seguinte para incluir o dia final inteiro
            condicoes.append(Notificacao.data_ocorrencia < datetime.combine(self.data_fim + timedelta(days=1), time.min))
        if self.agente_id is not None:
            condicoes.append(Notificacao.acs_ace_id == self.agente_id)

        return condicoes

    # Entradas da aba Resumo com os filtros que foram aplicados.
    # notificacoes: resultado já filtrado pelo escopo da conta; só com resultado o agente comprovadamente
    # pertence ao escopo, então só então o nome é buscado (evita revelar nomes de agentes de outra UBS/município)
    def resumo(self, session: Session, notificacoes: list) -> dict:
        resumo = {}

        if self.data_inicio and self.data_fim:
            resumo["Período"] = f"{self.data_inicio:%d/%m/%Y} a {self.data_fim:%d/%m/%Y}"
        elif self.data_inicio:
            resumo["Período"] = f"a partir de {self.data_inicio:%d/%m/%Y}"
        elif self.data_fim:
            resumo["Período"] = f"até {self.data_fim:%d/%m/%Y}"
        if self.agente_id is not None:
            nome = session.scalar(select(Agente.nome).where(Agente.id == self.agente_id)) if notificacoes else None
            resumo["Agente"] = nome or f"ID {self.agente_id}"

        return resumo


# Filtros de período para quem só enxerga as próprias notificações (ACS/ACE)
def filtros_relatorio_periodo(data_inicio: date | None = None, data_fim: date | None = None) -> FiltrosRelatorio:
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="data_inicio não pode ser posterior a data_fim.")

    return FiltrosRelatorio(data_inicio, data_fim)


# Filtros de período e agente para os perfis que enxergam notificações de vários agentes
def filtros_relatorio(data_inicio: date | None = None, data_fim: date | None = None, agente_id: int | None = None) -> FiltrosRelatorio:
    filtros = filtros_relatorio_periodo(data_inicio, data_fim)
    filtros.agente_id = agente_id

    return filtros
