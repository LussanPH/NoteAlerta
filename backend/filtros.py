from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from models import Notificacao, Agente, COADS, Superintendencias_Ceara

Categoria = Literal["DOENÇA", "EPIZOOTIA", "DESASTRE"]
Status = Literal["PENDENTE", "EM INVESTIGAÇÃO", "VERÍDICO", "NÃO VERÍDICO", "ENCERRADO"]

# "PENDENTE" também cobre o valor antigo "EM ANDAMENTO" (mesma regra do frontend)
STATUS_GRAVADOS = {"PENDENTE": ("PENDENTE", "EM ANDAMENTO")}

ROTULO_STATUS = {
    "PENDENTE": "Pendente",
    "EM INVESTIGAÇÃO": "Em investigação",
    "VERÍDICO": "Verídico",
    "NÃO VERÍDICO": "Não verídico",
    "ENCERRADO": "Encerrado",
}


@dataclass
class FiltrosRelatorio:
    data_inicio: date | None = None
    data_fim: date | None = None
    agente_id: int | None = None
    categoria: Categoria | None = None
    status: Status | None = None
    # coads e superintendencia só são aceitos nos endpoints cujas consultas fazem join com essas tabelas (VR e VE)
    coads: str | None = None
    superintendencia: str | None = None

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
        if self.categoria:
            condicoes.append(func.upper(Notificacao.categoria) == self.categoria)
        if self.status:
            condicoes.append(Notificacao.status.in_(STATUS_GRAVADOS.get(self.status, (self.status,))))
        if self.coads:
            condicoes.append(COADS.coads == self.coads)
        if self.superintendencia:
            condicoes.append(Superintendencias_Ceara.nome == self.superintendencia)

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
        if self.categoria:
            resumo["Categoria"] = self.categoria
        if self.status:
            resumo["Status"] = ROTULO_STATUS[self.status]
        if self.superintendencia:
            resumo["Superintendência"] = self.superintendencia
        if self.coads:
            resumo["COADS"] = self.coads

        return resumo


# Filtros de período (base de todos os perfis)
def filtros_relatorio_periodo(data_inicio: date | None = None, data_fim: date | None = None) -> FiltrosRelatorio:
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="data_inicio não pode ser posterior a data_fim.")

    return FiltrosRelatorio(data_inicio, data_fim)


# Uma dependência por perfil: cada uma só expõe os filtros que aquele perfil pode usar

# ACS/ACE e Coordenador Municipal: período, categoria e status
def filtros_basicos(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    categoria: Categoria | None = None,
    status: Status | None = None,
) -> FiltrosRelatorio:
    filtros = filtros_relatorio_periodo(data_inicio, data_fim)
    filtros.categoria = categoria
    filtros.status = status

    return filtros


# UBS: + agente
def filtros_ubs(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    categoria: Categoria | None = None,
    status: Status | None = None,
    agente_id: int | None = None,
) -> FiltrosRelatorio:
    filtros = filtros_basicos(data_inicio, data_fim, categoria, status)
    filtros.agente_id = agente_id

    return filtros


# Vigilante Regional: + COADS
def filtros_regional(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    categoria: Categoria | None = None,
    status: Status | None = None,
    coads: str | None = None,
) -> FiltrosRelatorio:
    filtros = filtros_basicos(data_inicio, data_fim, categoria, status)
    filtros.coads = coads

    return filtros


# Vigilante Estadual: + COADS e superintendência
def filtros_estadual(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    categoria: Categoria | None = None,
    status: Status | None = None,
    coads: str | None = None,
    superintendencia: str | None = None,
) -> FiltrosRelatorio:
    filtros = filtros_regional(data_inicio, data_fim, categoria, status, coads)
    filtros.superintendencia = superintendencia

    return filtros
