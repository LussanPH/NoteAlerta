# Sentinela Saúde — Backend

API do **NoteAlerta**, aplicativo para monitoramento de notificações registradas por **Agentes Comunitários de Saúde (ACS)** e **Agentes de Combate a Endemias (ACE)**.

O backend expõe endpoints REST consumidos pelo frontend em React, organizando as notificações por município, COADS e superintendência regional, e gera relatórios em PDF.

> 🔗 Frontend: `https://github.com/GuilhermeGasparr/yara-project-front/tree/main`
> 🌐 API em produção: `https://yara-project.onrender.com`

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Perfis de usuário](#perfis-de-usuário)
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
- [Autores](#autores)

---

## Funcionalidades

- Autenticação por CPF e senha com JWT (access token e refresh token), com perfis distintos de acesso
- Criação de notificações por ACS/ACE (com opção de rascunho), com envio de mídias (imagens e documentos) para o Cloudinary
- Geocodificação do endereço da notificação (latitude e longitude) via OpenStreetMap/Nominatim, para visualização geográfica por município
- Transcrição de áudio (modelo Whisper, via Groq) para preencher a descrição das notificações
- Fluxo de acompanhamento das notificações: validação, status (em investigação, verídico, não verídico, encerrado) e complementação de informações
- Criação hierárquica de contas: VE cria VE e VR, VR cria CM, CM e UBS criam ACS/ACE
- Listagem de notificações restrita ao escopo de cada perfil (agente, UBS, município, superintendência ou estado)
- Estatísticas para dashboard (Coordenador Municipal) e exportação de dados das notificações
- Relatórios em PDF: consolidado por perfil e individual por notificação

## Perfis de usuário

Cada perfil tem um prefixo de rotas próprio, protegido por uma dependência que valida o tipo do token JWT.

| Sigla     | Perfil                  | Prefixo   | Pode criar contas de      |
| --------- | ----------------------- | --------- | ------------------------- |
| `ACS/ACE` | Agente (ACS ou ACE)     | `/agentes` | —                         |
| `UBS`     | Unidade Básica de Saúde | `/ubs`    | ACS/ACE                   |
| `CM`      | Coordenador Municipal   | `/cm`     | ACS/ACE e UBS             |
| `VR`      | Vigilante Regional      | `/vr`     | Coordenador Municipal     |
| `VE`      | Vigilante Estadual      | `/ve`     | Vigilante Estadual e VR   |

## Tecnologias

| Camada         | Ferramenta                                                    | Uso no projeto                                          |
| -------------- | ------------------------------------------------------------- | ------------------------------------------------------- |
| Linguagem      | Python 3.13                                                   | Base do backend                                         |
| Framework web  | [FastAPI](https://fastapi.tiangolo.com/)                      | Criação dos endpoints REST                              |
| Servidor ASGI  | [Uvicorn](https://www.uvicorn.org/)                           | Execução da aplicação                                   |
| ORM            | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)          | Mapeamento das tabelas e consultas                      |
| Validação      | [Pydantic v2](https://docs.pydantic.dev/)                     | Schemas de entrada e saída                              |
| Migrações      | [Alembic](https://alembic.sqlalchemy.org/)                    | Versionamento do esquema do banco                       |
| Banco de dados | [PostgreSQL](https://www.postgresql.org/)                     | Persistência (em container Docker no ambiente local)    |
| Driver         | [psycopg 3](https://www.psycopg.org/psycopg3/)                | Conexão Python ↔ Postgres                               |
| Autenticação   | [python-jose](https://python-jose.readthedocs.io/) + [bcrypt](https://github.com/pyca/bcrypt) | JWT e hash de senhas                    |
| Transcrição    | [Groq](https://groq.com/) (`whisper-large-v3`)                | Transcrição de áudio para descrição                     |
| Armazenamento  | [Cloudinary](https://cloudinary.com/)                         | Mídias anexadas às notificações                         |
| Geocodificação | [Nominatim (OpenStreetMap)](https://nominatim.org/)           | Latitude/longitude a partir do endereço                 |
| Relatórios     | [ReportLab](https://docs.reportlab.com/)                      | Geração de PDFs                                         |
| Pacotes        | [uv](https://docs.astral.sh/uv/)                              | Gerenciamento de dependências e ambiente virtual        |
| Containers     | [Docker](https://www.docker.com/)                             | Banco Postgres local                                    |
| Deploy         | [Render](https://render.com/)                                 | Hospedagem da API e do banco em produção                |

## Estrutura do projeto

```
backend/
├── alembic/
│   ├── versions/          # Arquivos de migração gerados pelo Alembic
│   └── env.py             # Configuração das migrações (lê a DATABASE_URL)
├── routes/                # Endpoints agrupados por perfil
│   ├── auth_routes.py             # /auth (login e refresh)
│   ├── acs_ace_routes.py          # /agentes
│   ├── ubs_routes.py              # /ubs
│   ├── coordenador_routes.py      # /cm
│   ├── vigilantes_regional_routes.py   # /vr
│   └── vigilantes_estadual_routes.py   # /ve
├── config.py              # Leitura das variáveis de ambiente (.env)
├── dependencies.py        # Sessão do banco, validação do JWT e restrição por perfil
├── models.py              # Modelos SQLAlchemy e conexão com o banco de dados
├── schemas.py             # Modelos Pydantic (entrada/saída da API)
├── security.py            # Hash e verificação de senhas
├── main.py                # Instância do FastAPI, CORS e registro dos routers
├── docker-compose.yml     # Postgres local (e serviço opcional de clone do banco remoto)
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado (o Python 3.13 é obtido pelo `uv`, conforme `.python-version`)
- [Docker](https://docs.docker.com/get-docker/) instalado e em execução
- Git
- Contas/chaves de [Groq](https://console.groq.com/) e [Cloudinary](https://cloudinary.com/) para os recursos de transcrição de áudio e upload de mídias

## Como rodar localmente

### 1. Clonar o repositório

```bash
git clone git@github.com:LussanPH/Yara_project.git
cd Yara_project/backend
```

### 2. Instalar as dependências

```bash
uv sync
```

O `uv` cria o ambiente virtual (`.venv`) e instala as versões fixadas no `uv.lock`.

### 3. Configurar as variáveis de ambiente

Crie o arquivo `.env` dentro de `backend/` (ele está no `.gitignore`) com as variáveis descritas em [Variáveis de ambiente](#variáveis-de-ambiente). Exemplo para o ambiente local:

```env
POSTGRES_USER=sentinela
POSTGRES_PASSWORD=troque-esta-senha
POSTGRES_DB=sentinela

DATABASE_URL=postgresql+psycopg://sentinela:troque-esta-senha@localhost:5433/sentinela
PORT=8000

SECRET_KEY=gere-um-segredo-longo-e-aleatorio
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRATE_MINUTES=30

GROK_API_KEY=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### 4. Subir o banco Postgres em um container

```bash
docker compose up -d db-test
```

> O container `db_test` (Postgres 16) expõe a porta **5433** do host para não conflitar com um Postgres instalado nativamente na porta 5432. O volume `pgdata_test` mantém os dados quando o container é recriado.

Opcionalmente, para clonar um banco remoto (por exemplo, o de produção) para o container local, defina `REMOTE_DATABASE_URL` no `.env` e execute o serviço do perfil `tools`:

```bash
docker compose --profile tools run --rm db-clone
```

> ⚠️ Evite clonar dados reais de produção para o ambiente de desenvolvimento (veja [Segurança e dados sensíveis](#segurança-e-dados-sensíveis)).

### 5. Aplicar as migrações

```bash
uv run alembic upgrade head
```

### 6. Iniciar a API

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

A API ficará disponível em `http://localhost:8000` ou `http://127.0.0.1:8000`.

## Variáveis de ambiente

Lidas por `config.py` a partir do arquivo `.env`.

| Variável                        | Obrigatória | Descrição                                                                                     |
| ------------------------------- | :---------: | --------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                  |     Sim     | String de conexão com o Postgres. Prefixos `postgres://` e `postgresql://` são convertidos automaticamente para `postgresql+psycopg://`. Se ausente, usa `sqlite:///banco.db` |
| `PORT`                          |     Sim     | Porta da aplicação (lida como inteiro; no Render é definida pela plataforma)                  |
| `SECRET_KEY`                    |     Sim     | Segredo utilizado para assinar o JWT                                                          |
| `ALGORITHM`                     |     Sim     | Algoritmo de assinatura do JWT (ex.: `HS256`)                                                 |
| `ACCESS_TOKEN_EXPIRATE_MINUTES` |     Sim     | Tempo, em minutos, até o access token expirar (o refresh token expira em 1 dia)               |
| `GROK_API_KEY`                  |     Sim¹    | Chave da API do Groq para transcrição de áudio (o nome da variável é `GROK_API_KEY`, conforme `config.py`) |
| `CLOUDINARY_CLOUD_NAME`         |     Sim¹    | Nome da conta Cloudinary para armazenamento de mídias                                         |
| `CLOUDINARY_API_KEY`            |     Sim¹    | Chave da API do Cloudinary                                                                    |
| `CLOUDINARY_API_SECRET`         |     Sim¹    | Segredo da API do Cloudinary                                                                  |
| `POSTGRES_USER`                 |   Docker    | Usuário do Postgres local (usado pelo `docker-compose.yml`)                                   |
| `POSTGRES_PASSWORD`             |   Docker    | Senha do usuário do Postgres local                                                            |
| `POSTGRES_DB`                   |   Docker    | Nome do banco de dados local                                                                  |
| `REMOTE_DATABASE_URL`           |   Opcional  | Banco remoto de origem para o serviço `db-clone` (perfil `tools`)                             |
| `NGROK_DOMAIN`, `NGROK_TOKEN`   |   Opcional  | Lidas por `config.py` para exposição local via ngrok; não são necessárias para rodar a API    |

¹ Necessária para o recurso correspondente (transcrição de áudio e upload de mídias).

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

### Autenticação

O login usa o formato `application/x-www-form-urlencoded` (OAuth2 password):

| Campo        | Descrição                                                              |
| ------------ | ---------------------------------------------------------------------- |
| `username`   | CPF do usuário                                                         |
| `password`   | Senha                                                                  |
| `tipo_login` | Perfil: `ACS/ACE`, `UBS`, `CM`, `VR` ou `VE` (se omitido, usa `client_id`) |

A resposta traz `access_token`, `refresh_token`, `type_token` (`Bearer`) e os dados do usuário. Nas demais rotas, envie o header `Authorization: Bearer <access_token>`. Cada prefixo só aceita tokens do perfil correspondente.

### Principais endpoints

**Autenticação** (`/auth`)

| Método | Rota            | Descrição                                           |
| ------ | --------------- | --------------------------------------------------- |
| `POST` | `/auth/login`   | Autentica o usuário e retorna os tokens             |
| `POST` | `/auth/refresh` | Gera um novo access token a partir do refresh token |

**Agentes ACS/ACE** (`/agentes`)

| Método | Rota                                         | Descrição                                       |
| ------ | -------------------------------------------- | ----------------------------------------------- |
| `GET`  | `/agentes/listar_notificacoes`               | Lista as notificações do agente                 |
| `POST` | `/agentes/criar_notificacao`                 | Cria uma notificação (formulário com mídias; permite rascunho) |
| `POST` | `/agentes/transcricao_audio`                 | Transcreve um áudio enviado em texto            |
| `GET`  | `/agentes/exportar_relatorio`                | Exporta os dados das notificações               |
| `GET`  | `/agentes/exportar_relatorio/pdf`            | Gera o relatório consolidado em PDF             |
| `GET`  | `/agentes/notificacoes/{notificacao_id}/relatorio_pdf` | Gera o relatório em PDF de uma notificação |

**UBS** (`/ubs`)

| Método  | Rota                                                  | Descrição                                          |
| ------- | ----------------------------------------------------- | -------------------------------------------------- |
| `POST`  | `/ubs/criar_conta_acs_ace`                            | Cria a conta de um ACS/ACE                         |
| `GET`   | `/ubs/notificacoes`                                   | Lista as notificações (não rascunho) dos agentes da UBS |
| `GET`   | `/ubs/dados_ubs`                                      | Retorna os dados da UBS autenticada                |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/validar`          | Valida a notificação                               |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/complementar`     | Adiciona informação extra (`informacao_extra`)     |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/status_em_investigacao` | Define o status como em investigação         |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/status_veridico`  | Define o status como verídico                      |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/status_nao_veridico` | Define o status como não verídico               |
| `PATCH` | `/ubs/notificacoes/{notificacao_id}/status_encerrado` | Define o status como encerrado                     |
| `GET`   | `/ubs/exportar_relatorio`                             | Exporta os dados das notificações                  |
| `GET`   | `/ubs/exportar_relatorio/pdf`                         | Gera o relatório consolidado em PDF                |
| `GET`   | `/ubs/notificacoes/{notificacao_id}/relatorio_pdf`    | Gera o relatório em PDF de uma notificação         |

**Coordenador Municipal** (`/cm`)

| Método  | Rota                                                  | Descrição                                          |
| ------- | ----------------------------------------------------- | -------------------------------------------------- |
| `POST`  | `/cm/criar_conta_acs_ace`                             | Cria a conta de um ACS/ACE                         |
| `POST`  | `/cm/criar_conta_ubs`                                 | Cria a conta de uma UBS                            |
| `GET`   | `/cm/listar_notificacoes`                             | Lista as notificações do município                 |
| `GET`   | `/cm/dashboard_stats`                                 | Retorna estatísticas para o dashboard              |
| `PATCH` | `/cm/notificacoes/{notificacao_id}/status_em_investigacao` | Define o status como em investigação          |
| `PATCH` | `/cm/notificacoes/{notificacao_id}/status_veridico`   | Define o status como verídico                      |
| `PATCH` | `/cm/notificacoes/{notificacao_id}/status_nao_veridico` | Define o status como não verídico                |
| `PATCH` | `/cm/notificacoes/{notificacao_id}/status_encerrado`  | Define o status como encerrado                     |
| `PATCH` | `/cm/notificacoes/{notificacao_id}/complementar`      | Adiciona informação extra (`informacao_extra`)     |
| `GET`   | `/cm/exportar_relatorio`                              | Exporta os dados das notificações                  |
| `GET`   | `/cm/exportar_relatorio/pdf`                          | Gera o relatório consolidado em PDF                |
| `GET`   | `/cm/notificacoes/{notificacao_id}/relatorio_pdf`     | Gera o relatório em PDF de uma notificação         |

**Vigilante Regional** (`/vr`)

| Método | Rota                                               | Descrição                                              |
| ------ | -------------------------------------------------- | ------------------------------------------------------ |
| `POST` | `/vr/criar_conta_coordenador`                      | Cria a conta de um Coordenador Municipal               |
| `GET`  | `/vr/notificacoes`                                 | Lista as notificações da superintendência, com o COADS |
| `GET`  | `/vr/dados_superintendencia_coads`                 | Retorna os dados da superintendência e seus COADS      |
| `GET`  | `/vr/exportar_relatorio`                           | Exporta os dados das notificações                      |
| `GET`  | `/vr/exportar_relatorio/pdf`                       | Gera o relatório consolidado em PDF                    |
| `GET`  | `/vr/notificacoes/{notificacao_id}/relatorio_pdf`  | Gera o relatório em PDF de uma notificação             |

**Vigilante Estadual** (`/ve`)

| Método | Rota                                               | Descrição                                              |
| ------ | -------------------------------------------------- | ------------------------------------------------------ |
| `POST` | `/ve/criar_conta_ve`                               | Cria a conta de um Vigilante Estadual                  |
| `POST` | `/ve/criar_conta_vr`                               | Cria a conta de um Vigilante Regional                  |
| `GET`  | `/ve/notificacoes`                                 | Lista as notificações de todo o estado, com COADS e superintendência |
| `GET`  | `/ve/exportar_relatorio`                           | Exporta os dados das notificações                      |
| `GET`  | `/ve/exportar_relatorio/pdf`                       | Gera o relatório consolidado em PDF                    |
| `GET`  | `/ve/notificacoes/{notificacao_id}/relatorio_pdf`  | Gera o relatório em PDF de uma notificação             |

> Para parâmetros, corpos de requisição e respostas detalhados, consulte o Swagger UI.

## Deploy

O backend é hospedado no **Render**, com banco PostgreSQL gerenciado.

| Configuração  | Valor                                                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Build command | `uv sync --frozen && uv cache prune --ci`                                                                                      |
| Start command | `uv run alembic upgrade head && uv run uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` |

As variáveis de ambiente listadas acima devem ser configuradas no painel do Render. As migrações são aplicadas automaticamente a cada deploy, antes de a API iniciar.

## Segurança e dados sensíveis

O sistema lida com **dados de saúde**, considerados dados pessoais sensíveis pela LGPD (Lei nº 13.709/2018). Por isso:

- Não versione credenciais, `.env`, bancos locais (`*.db`) ou dumps do banco
- Não use dados reais em ambiente de desenvolvimento
- Endpoints de detalhe devem verificar se o recurso pertence ao escopo (agente, UBS, município ou superintendência) do usuário autenticado
- Use um `SECRET_KEY` longo e aleatório, diferente em cada ambiente
- O CORS está liberado para qualquer origem (`allow_origins=["*"]`); restrinja ao domínio do frontend em produção
- Faça backup (`pg_dump`) antes de operações destrutivas no banco

## Contribuindo

1. Crie uma branch a partir da `main`: `git checkout -b feature/nome-da-feature`
2. Faça commits pequenos e descritivos
3. Se alterar `models.py`, gere e revise a migração do Alembic
4. Abra um Pull Request descrevendo o que mudou e como testar

## Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

## Autores

- **Pedro Luna** — [@LussanPH](https://github.com/LussanPH)
- **Guilherme Gaspar** — [@GuilhermeGasparr](https://github.com/GuilhermeGasparr)
