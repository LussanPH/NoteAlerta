from sqlalchemy import create_engine
from models import Base


pg   = create_engine("postgresql+psycopg://sentinela:sentinela@localhost:5433/sentinela_db")
lite = create_engine("sqlite:///dev.db")

Base.metadata.create_all(lite)       

with pg.connect() as origem, lite.begin() as destino:
    for tabela in Base.metadata.sorted_tables:     
        linhas = origem.execute(tabela.select()).mappings().all()
        if linhas:
            destino.execute(tabela.insert(), [dict(l) for l in linhas])