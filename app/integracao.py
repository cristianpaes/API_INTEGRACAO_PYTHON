import os
import httpx

from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

from .database import engine


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


API_URL = os.getenv("API_PRODUCTS_URL")

if not API_URL:
    raise RuntimeError(
        "API_PRODUCTS_URL não encontrada no arquivo .env"
    )


# ==========================================================
# SINCRONIZAÇÃO
# ==========================================================

def sincronizar_produtos(limit: int = 10):

    data_inicio = datetime.now(timezone.utc)

    inseridos = 0
    atualizados = 0
    erros = 0
    produtos = []

    status = "sucesso"
    mensagem = "Integração executada com sucesso"

    try:

        # --------------------------------------------------
        # 1. Consulta API externa
        # --------------------------------------------------

        response = httpx.get(
            API_URL,
            params={"limit": limit},
            timeout=15.0
        )

        response.raise_for_status()

        dados_api = response.json()

        produtos = dados_api.get("products", [])


        # --------------------------------------------------
        # 2. Grava no banco
        # --------------------------------------------------

        with engine.begin() as connection:

            for produto in produtos:

                try:

                    api_id = produto.get("id")

                    # Verifica se já existe
                    consulta = connection.execute(
                        text("""
                            SELECT 1
                            FROM integracao_produtos
                            WHERE api_id = :api_id
                        """),
                        {
                            "api_id": api_id
                        }
                    )

                    existe = consulta.first() is not None


                    # INSERT / UPDATE
                    connection.execute(
                        text("""
                            INSERT INTO integracao_produtos (
                                api_id,
                                nome_produto,
                                categoria,
                                marca,
                                preco,
                                estoque
                            )
                            VALUES (
                                :api_id,
                                :nome_produto,
                                :categoria,
                                :marca,
                                :preco,
                                :estoque
                            )

                            ON CONFLICT (api_id)
                            DO UPDATE SET
                                nome_produto = EXCLUDED.nome_produto,
                                categoria = EXCLUDED.categoria,
                                marca = EXCLUDED.marca,
                                preco = EXCLUDED.preco,
                                estoque = EXCLUDED.estoque,
                                data_atualizacao = NOW()
                        """),
                        {
                            "api_id": api_id,
                            "nome_produto": produto.get("title"),
                            "categoria": produto.get("category"),
                            "marca": produto.get("brand"),
                            "preco": produto.get("price"),
                            "estoque": produto.get("stock")
                        }
                    )


                    # Contadores
                    if existe:
                        atualizados += 1
                    else:
                        inseridos += 1


                except Exception as error:

                    erros += 1

                    print(
                        f"ERRO AO PROCESSAR PRODUTO "
                        f"{produto.get('id')}: {error}"
                    )


        # --------------------------------------------------
        # 3. Define status
        # --------------------------------------------------

        if erros > 0:

            status = "parcial"

            mensagem = (
                "Integração executada com alguns erros"
            )


    except httpx.HTTPError as error:

        status = "erro"

        mensagem = (
            f"Erro ao consultar API externa: {error}"
        )


    except Exception as error:

        status = "erro"

        mensagem = (
            f"Erro durante a integração: {error}"
        )


    # ======================================================
    # LOG
    # ======================================================

    data_fim = datetime.now(timezone.utc)

    total_recebido = len(produtos)


    with engine.begin() as connection:

        connection.execute(
            text("""
                INSERT INTO log_integracao (
                    tipo_integracao,
                    data_inicio,
                    data_fim,
                    status,
                    total_recebido,
                    total_inserido,
                    total_atualizado,
                    total_erros,
                    mensagem
                )
                VALUES (
                    :tipo_integracao,
                    :data_inicio,
                    :data_fim,
                    :status,
                    :total_recebido,
                    :total_inserido,
                    :total_atualizado,
                    :total_erros,
                    :mensagem
                )
            """),
            {
                "tipo_integracao": "produtos",
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "status": status,
                "total_recebido": total_recebido,
                "total_inserido": inseridos,
                "total_atualizado": atualizados,
                "total_erros": erros,
                "mensagem": mensagem
            }
        )


    # ======================================================
    # RETORNO
    # ======================================================

    return {
        "status": status,
        "mensagem": mensagem,
        "total_recebido_api": total_recebido,
        "inseridos": inseridos,
        "atualizados": atualizados,
        "erros": erros
    }