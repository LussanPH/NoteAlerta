"""Adiciona public_id, resource_type e nome_arquivo em Notificacoes_Media

Revision ID: b7c3e1d94a52
Revises: a63afbbef081
Create Date: 2026-11-22 19:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7c3e1d94a52'
down_revision: Union[str, Sequence[str], None] = 'a63afbbef081'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# https://res.cloudinary.com/<cloud>/<tipo>/upload/[v123/]<public_id>[.ext]
_URL_CLOUDINARY = re.compile(r"/(image|video|raw)/upload/(?:v\d+/)?(.+)$")


def _extrair_dados(url: str | None) -> tuple[str | None, str | None]:
    """Deduz (public_id, resource_type) de uma URL do Cloudinary.

    Em image/video o public_id não leva a extensão; em raw leva.
    URLs fora do padrão devolvem (None, None).
    """
    if not url:
        return None, None

    correspondencia = _URL_CLOUDINARY.search(url.split("?", 1)[0])
    if not correspondencia:
        return None, None

    resource_type, caminho = correspondencia.groups()
    if resource_type != "raw":
        caminho = caminho.rsplit(".", 1)[0] if "." in caminho.rsplit("/", 1)[-1] else caminho

    return caminho, resource_type


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('Notificacoes_Media', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('resource_type', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('nome_arquivo', sa.String(), nullable=True))

    # Preenche os registros anteriores, para que também possam ser apagados do Cloudinary
    midias = sa.table(
        'Notificacoes_Media',
        sa.column('id', sa.Integer),
        sa.column('url', sa.String),
        sa.column('public_id', sa.String),
        sa.column('resource_type', sa.String),
    )
    conexao = op.get_bind()

    for id_, url in conexao.execute(sa.select(midias.c.id, midias.c.url)).all():
        public_id, resource_type = _extrair_dados(url)
        if public_id:
            conexao.execute(
                midias.update()
                .where(midias.c.id == id_)
                .values(public_id=public_id, resource_type=resource_type)
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('Notificacoes_Media', schema=None) as batch_op:
        batch_op.drop_column('nome_arquivo')
        batch_op.drop_column('resource_type')
        batch_op.drop_column('public_id')
