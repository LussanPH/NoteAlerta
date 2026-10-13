# Sentinela Saúde — Backend

API do **NoteAlerta**, aplicativo para monitoramento de notificações registradas por **Agentes Comunitários de Saúde (ACS)** e **Agentes de Combate a Endemias (ACE)**.

O backend expõe endpoints REST consumidos pelo frontend em React, organizando as notificações por município e superintendência regional, e gera relatórios em PDF.

> 🔗 Frontend: `https://github.com/GuilhermeGasparr/yara-project-front/tree/main`
> 🌐 API em produção: `https://yara-project.onrender.com`

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Como rodar localmente](#como-rodar-localmente)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Migrações do banco (Alembic)](#migrações-do-banco-alembic)
- [Documentação da API](#documentação-da-api)
- [Deploy](#deploy)
- [Segurança e dados sensíveis](#segurança-e-dados-sensíveis)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## Funcionalidades

- Cadastro e consulta de notificações de ACS/ACE, UBS, Coordenador Municipal, Vigilante Regional e Vigilante Estadual
- Filtro e análise de dashboards e dados de notificações
- Geração de relatórios em PDF das notificações
- Visualização geográfica das notificações por município
- Transcrição de Áudio via LLM para registro de descrição das notificações

## Tecnologias

| Camada         | Ferramenta                                           | Uso no projeto                                       |
| -------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Linguagem      | Python 3.13                                          | Base do backend                                      |
| Framework web  | [FastAPI](https://fastapi.tiangolo.com/)             | Criação dos endpoints REST                           |
| Servidor ASGI  | [Uvicorn](https://www.uvicorn.org/)                  | Execução da aplicação                                |
| ORM            | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) | Mapeamento das tabelas e consultas                   |
| Validação      | [Pydantic v2](https://docs.pydantic.dev/)            | Schemas de entrada e saída                           |
| Migrações      | [Alembic](https://alembic.sqlalchemy.org/)           | Versionamento do esquema do banco                    |
| Banco de dados | [PostgreSQL](https://www.postgresql.org/)            | Persistência (em container Docker no ambiente local) |
| Driver         | [psycopg 3](https://www.psycopg.org/psycopg3/)       | Conexão Python ↔ Postgres                            |
| Relatórios     | [ReportLab](https://docs.reportlab.com/)             | Geração de PDFs                                      |
| Pacotes        | [uv](https://docs.astral.sh/uv/)                     | Gerenciamento de dependências e ambiente virtual     |
| Containers     | [Docker](https://www.docker.com/)                    | Banco Postgres local                                 |
| Deploy         | [Render](https://render.com/)                        | Hospedagem da API e do banco em produção             |

## Estrutura do projeto

```
backend/
├── alembic/
│   ├── versions/        # Arquivos de migração gerados pelo Alembic
│   └── env.py           # Configuração das migrações (lê a DATABASE_URL)
├── routers/             # Endpoints agrupados por recurso
├── schemas/             # Modelos Pydantic (entrada/saída da API)
├── config.py            # Registro das variáveis de ambiente
├── models.py            # Base e modelos SQLAlchemy, juntamente com a conexão ao banco de dados
├── main.py              # Instância do FastAPI e registro dos routers
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado
- [Docker](https://docs.docker.com/get-docker/) instalado e em execução
- Git

## Como rodar localmente

### 1. Clonar o repositório

```bash
git clone git@github.com:LussanPH/Yara_project.git
cd NoteAlerta/backend
```

### 2. Instalar as dependências

```bash
uv sync
```

O `uv` cria o ambiente virtual (`.venv`) e instala as versões fixadas no `uv.lock`.

### 3. Subir o banco Postgres em um container

```bash
docker compose up -d
```

> A porta **5433** do host é usada para não conflitar com um Postgres instalado nativamente na porta 5432. O volume `sentinela-pgdata` mantém os dados quando o container é recriado.

### 4. Configurar as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com os dados do container (veja [Variáveis de ambiente](#variáveis-de-ambiente)).

### 5. Aplicar as migrações

```bash
uv run alembic upgrade head
```

### 6. Iniciar a API

```bash
uv run uvicorn main:app --port 0.0.0.0 --port 8000 --reload
```

A API ficará disponível em `http://localhost:8000` ou `http://127.0.0.1:8000`.

## Variáveis de ambiente

| Variável                        | Descrição                                                                  |
| ------------------------------- | -------------------------------------------------------------------------- |
| `DATABASE_URL`                  | String de conexão com o Postgres                                           |
| `SECRET_KEY`                    | Segredo utilizado para a criação do JWT                                    |
| `ALGORITHM`                     | O cálculo utilizado para a criação do JWT                                  |
| `ACCESS_TOKEN_EXPIRATE_MINUTES` | Tempo que uma JWT expira                                                   |
| `GROQ_API_KEY`                  | Chave API do Groq para transcrição de áudio                                |
| `CLOUDINARY_CLOUD_NAME`         | Variáveis do serviço cloudinary para armazenamento de imagens e documentos |
| `CLOUDINARY_API_KEY`            | Variáveis do serviço cloudinary para armazenamento de imagens e documentos |
| `CLOUDINARY_API_SECRET`         | Variáveis do serviço cloudinary para armazenamento de imagens e documentos |
| `POSTGRES_USER`                 | Nome do usuário do postgres local                                          |
| `POSTGRES_PASSWORD`             | Senha do usuário postgres local                                            |
| `POSTGRES_DB`                   | Nome do banco de dados local                                               |

## Migrações do banco (Alembic)

O esquema do banco é versionado com Alembic. O `alembic/env.py` lê a mesma `DATABASE_URL` da aplicação, garantindo que migrações e API usem o mesmo banco.

```bash
# Gerar uma nova migração a partir das alterações em models.py
uv run alembic revision --autogenerate -m "descricao da alteracao"

# Aplicar todas as migrações pendentes
uv run alembic upgrade head

# Desfazer a última migração
uv run alembic downgrade -1

# Ver a revisão atual do banco
uv run alembic current
```

> Sempre revise o arquivo gerado em `alembic/versions/` antes de aplicar: o `--autogenerate` não detecta tudo (por exemplo, renomeação de colunas).

## Documentação da API

Com a API rodando, o FastAPI gera a documentação interativa automaticamente:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Principais endpoints

> `TODO: completar com os endpoints reais`

| Método | Rota                 | Descrição               |
| ------ | -------------------- | ----------------------- |
| `GET`  | `/notificacoes`      | Lista as notificações   |
| `GET`  | `/notificacoes/{id}` | Detalha uma notificação |
| `GET`  | `TODO`               | Gera relatório em PDF   |

## Deploy

O backend é hospedado no **Render**, com banco PostgreSQL gerenciado.

| Configuração  | Valor                                                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Build command | `uv sync --frozen && uv cache prune --ci`                                                                                      |
| Start command | `uv run alembic upgrade head && uv run uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` |

As migrações são aplicadas automaticamente a cada deploy, antes de a API iniciar.

## Segurança e dados sensíveis

O sistema lida com **dados de saúde**, considerados dados pessoais sensíveis pela LGPD (Lei nº 13.709/2018). Por isso:

- Não versione credenciais, `.env` ou dumps do banco
- Não use dados reais em ambiente de desenvolvimento
- Endpoints de detalhe devem verificar se o recurso pertence à superintendência do usuário autenticado
- Faça backup (`pg_dump`) antes de operações destrutivas no banco

## Contribuindo

1. Crie uma branch a partir da `main`: `git checkout -b feature/nome-da-feature`
2. Faça commits pequenos e descritivos
3. Se alterar `models.py`, gere e revise a migração do Alembic
4. Abra um Pull Request descrevendo o que mudou e como testar

## Licença

`TODO: definir licença (ex.: MIT) ou indicar "uso restrito"`

## Autor

**Pedro** — `TODO: GitHub / LinkedIn`
