# Roteiro da apresentação (5 minutos)

## 1. Problema 
O produtor rural decide com informação espalhada: previsão em um app, preço em outro site, histórico em planilha. Decisões erradas custam caro: uma geada não prevista pode destruir uma safra de café, e pulverizar com vento forte desperdiça insumo. O AgroDecisão junta essas fontes e entrega recomendações por talhão.

## 2. Arquitetura 
- Duas APIs externas: Open-Meteo (clima) e AwesomeAPI (dólar).
- Três armazenamentos, cada um com um papel:
  - **MongoDB**: talhões, JSON bruto da API de clima e série diária tratada. Documentos flexíveis combinam com respostas de API.
  - **SQLite**: histórico tabular (produtividade e cotações), que é naturalmente relacional.
  - **DuckDB**: motor analítico que cruza os dois bancos acima com SQL, em memória.
- **Apache Hop**: carrega os CSVs de produtividade e cotações no SQLite.
- **FastAPI** (Python): ETL, motor de regras e API REST.
- **React**: painel do produtor.

## 3. Integrações 
- Hop: CSV → SQLite.
- Python: Open-Meteo → MongoDB (bruto) → MongoDB (tratado, com upsert).
- DuckDB: junta talhões (MongoDB) + produtividade e cotações (SQLite) para calcular a margem.
- Frontend consome tudo pela API.

## 4. Funcionalidades
- Alertas de geada, déficit hídrico e chuva forte.
- Janelas de pulverização.
- Margem por hectare e por safra.
- Cotações e dólar.

## 5. Demonstração
1. Abrir o painel e mostrar o resumo de alertas por talhão.
2. Clicar em "Atualizar clima" e mostrar o dado novo entrando.
3. Abrir um talhão: recomendações, gráfico de clima e margem.
4. Mostrar `/api/health` com os três bancos ativos.
5. Mostrar no MongoDB (Atlas ou Compass) o documento bruto da coleção `clima_raw`.
6. Mostrar o pipeline no Hop e as tabelas do SQLite.

