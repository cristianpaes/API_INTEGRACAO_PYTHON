import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


# Localiza a raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o arquivo .env
load_dotenv(BASE_DIR / ".env")


# Lê as informações do banco
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")


# Validação das configurações
variaveis_obrigatorias = {
    "DB_HOST": DB_HOST,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_PORT": DB_PORT,
}

faltando = [
    nome
    for nome, valor in variaveis_obrigatorias.items()
    if not valor
]

if faltando:
    raise RuntimeError(
        f"Variáveis do banco não encontradas no .env: {', '.join(faltando)}"
    )


# Monta a URL de conexão PostgreSQL
DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}"
)


# Cria a conexão com o banco
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)