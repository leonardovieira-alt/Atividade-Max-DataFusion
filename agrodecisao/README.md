# 🌱 AgroDecisão

Painel de apoio à decisão para o produtor rural. Cruza **previsão do tempo**, **cotações de mercado** e **histórico de produtividade/custo** de cada talhão para responder perguntas práticas:

- Vai ter **geada** nos próximos dias? Preciso proteger a lavoura?
- Quando há **janela boa para pulverizar** (vento baixo, sem chuva, temperatura amena)?
- A lavoura está em **déficit hídrico**? Devo irrigar?
- Devo **adiar a colheita** por causa de chuva forte?
- Qual a **margem por hectare** de cada talhão ao preço de hoje?

Cenário de exemplo: fazenda na região de São João da Boa Vista (SP), com talhões de café, milho, soja e batata.

**Não usa Docker.** O único componente que precisa de servidor é o MongoDB (local ou na nuvem, ver abaixo).

## Arquitetura

```
 Open-Meteo (API clima)     AwesomeAPI (dólar)        CSVs (produtividade, cotações)
        │                          │                               │
        ▼                          │                               ▼
  ETL Python (etl.py)              │                     Apache Hop (pipeline_agro.hpl)
        │                          │                               │
        ▼                          │                               ▼
     MongoDB                       │                            SQLite
  • talhoes                        │                      • produtividade
  • clima_raw    (JSON bruto)      │                      • cotacoes
  • clima_diario (tratado)         │                               │
        │                          │                               │
        └──────────────┬───────────┴───────────────┬───────────────┘
                       ▼                           ▼
                API FastAPI (Python) ──► DuckDB (SQL analítico em memória:
                       │                  cruza MongoDB + SQLite → receita e margem)
                       ▼
                Frontend React (painel)
```

| Camada | Tecnologia | Papel |
|---|---|---|
| Armazenamento 1 | **MongoDB** | Talhões, resposta bruta (JSON) da API de clima e série diária tratada |
| Armazenamento 2 | **SQLite** | Histórico tabular: produtividade e cotações (arquivo `data/agro.sqlite`) |
| Armazenamento 3 | **DuckDB** | Engine analítica: cruza dados dos dois bancos acima e calcula receita/margem |
| Integração | **Apache Hop** | Pipeline que carrega produtividade e cotações (CSV) no SQLite |
| API externa | **Open-Meteo** | Previsão e histórico recente (temperatura, chuva, vento, evapotranspiração) |
| API externa | **AwesomeAPI** | Cotação USD/BRL |
| Backend | **Python / FastAPI** | ETL, motor de regras e endpoints REST |
| Frontend | **React + Vite + Recharts** | Painel de visualização |

## Como o sistema funciona

1. **Cadastro**: ao iniciar, o backend cria as tabelas do SQLite, os índices do MongoDB e carrega os talhões de exemplo (`data/talhoes.csv`) na coleção `talhoes`.
2. **Integração com o Hop**: o `pipeline_agro.hpl` lê `produtividade.csv` e `cotacoes.csv` e grava no SQLite.
3. **Integração de clima** (botão "Atualizar clima" ou `python -m app.etl`): para cada talhão, usa as coordenadas para consultar a Open-Meteo (7 dias passados + 7 de previsão). O JSON original vai para `clima_raw`; a série diária normalizada vai para `clima_diario` com *upsert* (reexecutar não duplica).
4. **Motor de regras** (`regras.py`): funções puras que transformam a série de clima em recomendações por cultura:
   - Geada: mínima ≤ 3 °C (média) ou ≤ 1 °C (alta)
   - Pulverização: vento ≤ 10 km/h, chuva ≤ 30 % e máxima ≤ 30 °C
   - Déficit hídrico: chuva − evapotranspiração (7 dias) ≤ −15 mm
   - Colheita: chuva prevista ≥ 20 mm → adiar operações de campo
5. **Analytics (DuckDB)**: recebe talhões (MongoDB) e produtividade/cotações (SQLite), junta com SQL e calcula receita, margem por hectare e margem total por safra, usando o preço mais recente.
6. **Painel React**: resumo de alertas por talhão, recomendações, gráfico de clima, gráfico de margem por safra e cotações (com dólar ao vivo).

Os limites das regras são constantes no topo de `regras.py` e devem ser calibrados com um agrônomo para cada cultura e estágio fenológico.

## Como executar

Pré-requisitos: Python 3.11+, Node 18+, um MongoDB (opção A ou B abaixo) e, para o fluxo oficial, Apache Hop 2.x (requer Java 17).

### 1) MongoDB (escolha uma opção)

**Opção A, nuvem (MongoDB Atlas, gratuito, sem instalar nada):**
1. Crie uma conta em https://www.mongodb.com/atlas e um cluster gratuito (M0).
2. Em *Database Access*, crie um usuário e senha. Evite caracteres especiais na senha (ou codifique-os na URL).
3. Em *Network Access*, libere o seu IP (para a demonstração, "Allow access from anywhere").
4. Em *Connect → Drivers*, copie a string de conexão e defina a variável de ambiente:

```powershell
# Windows (PowerShell)
$env:MONGO_URI="mongodb+srv://USUARIO:SENHA@cluster0.xxxxx.mongodb.net/"
```
```bash
# Linux / Mac
export MONGO_URI="mongodb+srv://USUARIO:SENHA@cluster0.xxxxx.mongodb.net/"
```

**Opção B, instalado no computador:** instale o *MongoDB Community Server* (https://www.mongodb.com/try/download/community) com as opções padrão. Ele sobe em `mongodb://localhost:27017`, que já é o valor padrão do projeto, então não precisa configurar nada.

### 2) Backend

```bash
cd backend
pip install -r requirements.txt
python -m app.carga_csv        # contingência (sem Hop); o fluxo oficial é o passo 3
uvicorn app.main:app --reload --port 8000
```

### 3) Carga dos CSVs com Apache Hop (fluxo oficial)

1. Abra o Hop GUI e crie um projeto com a pasta `hop/` como home.
2. Confira a conexão `agro_sqlite` (Metadata → Relational Database Connection): ela deve apontar para `data/agro.sqlite`.
3. Rode antes o backend ao menos uma vez (ele cria o arquivo e as tabelas do SQLite) e execute o `pipeline_agro.hpl`.

### 4) Clima e painel

```bash
curl -X POST http://localhost:8000/api/etl/clima     # ou use o botão "Atualizar clima"

cd ../frontend
npm install
npm run dev        # http://localhost:5173
```

Verifique a conexão com os bancos em http://localhost:8000/api/health.

### Testes

```bash
cd backend && python -m pytest
```

Os testes de API usam um MongoDB simulado (`mongomock`) e um SQLite temporário, e substituem a chamada à Open-Meteo por dados fixos. Não precisam de servidor nem de internet.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | Estado de MongoDB, SQLite e DuckDB |
| GET | `/api/talhoes` | Lista de talhões |
| POST | `/api/etl/clima` | Executa a integração de clima |
| GET | `/api/talhoes/{id}/clima` | Série diária de clima |
| GET | `/api/talhoes/{id}/recomendacoes` | Recomendações do motor de regras |
| GET | `/api/resumo` | Alertas por talhão |
| GET | `/api/cotacoes` | Últimas cotações + dólar |
| GET | `/api/analytics/margem` | Receita e margem por talhão/safra (DuckDB) |

## Estrutura

```
agrodecisao/
├── data/                   # CSVs de entrada (talhões, produtividade, cotações) e agro.sqlite
├── hop/                    # pipeline Apache Hop + conexão SQLite
├── backend/app/            # FastAPI, ETL, regras, analytics, acesso aos bancos
├── backend/tests/          # testes do motor de regras, do DuckDB e da API
├── frontend/               # React + Vite
└── docs/APRESENTACAO.md    # roteiro dos 5 minutos
```

## Observação sobre os dados

`produtividade.csv` e `cotacoes.csv` contêm **dados fictícios de exemplo**. Para uso real, substitua pelas séries da fazenda e por cotações oficiais (por exemplo, exportações do CEPEA/ESALQ) mantendo as mesmas colunas.
