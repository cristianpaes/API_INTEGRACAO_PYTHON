import httpx

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text

from .database import engine
from .integracao import sincronizar_produtos



app = FastAPI(
    title="API de Integração de Vendas",
    description="API Python integrada ao PostgreSQL/Neon",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "status": "online",
        "mensagem": "API de integração funcionando"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/health/db")
def health_db():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT
                        current_database() AS database_name,
                        NOW() AS server_time
                """)
            )

            row = result.mappings().one()

            return {
                "status": "ok",
                "database": row["database_name"],
                "server_time": str(row["server_time"])
            }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na conexão com o banco: {str(error)}"
        )


@app.get("/vendas")
def listar_vendas(
    ano: int | None = None,
    vendedor: str | None = None,
    regiao: str | None = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    try:
        sql = """
            SELECT
                ano,
                nome_mes,
                nome_produto,
                nome_cliente,
                nome_vendedor,
                nome_regiao,
                faturamento,
                lucro
            FROM "VW_VENDAS_ANALITICAS"
            WHERE 1 = 1
        """

        parametros = {}

        if ano is not None:
            sql += " AND ano = :ano"
            parametros["ano"] = ano

        if vendedor is not None:
            sql += " AND nome_vendedor = :vendedor"
            parametros["vendedor"] = vendedor

        if regiao is not None:
            sql += " AND nome_regiao = :regiao"
            parametros["regiao"] = regiao

        sql += """
            ORDER BY ano DESC, nome_mes, nome_produto
            LIMIT :limit
        """

        parametros["limit"] = limit

        with engine.connect() as connection:
            result = connection.execute(
                text(sql),
                parametros
            )

            dados = [dict(row) for row in result.mappings()]

            return {
                "quantidade": len(dados),
                "filtros": {
                    "ano": ano,
                    "vendedor": vendedor,
                    "regiao": regiao
                },
                "dados": dados
            }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar vendas: {str(error)}"
        )

@app.get("/vendas/resumo")
def resumo_vendas(
    ano: int | None = None
):
    try:
        sql = """
            SELECT
                COALESCE(SUM(faturamento), 0) AS faturamento_total,
                COALESCE(SUM(lucro), 0) AS lucro_total,
                COUNT(*) AS quantidade_registros
            FROM "VW_VENDAS_ANALITICAS"
            WHERE 1 = 1
        """

        parametros = {}

        if ano is not None:
            sql += " AND ano = :ano"
            parametros["ano"] = ano

        with engine.connect() as connection:
            result = connection.execute(
                text(sql),
                parametros
            )

            dados = result.mappings().one()

            faturamento = float(dados["faturamento_total"])
            lucro = float(dados["lucro_total"])

            return {
                "faturamento_total": faturamento,
                "lucro_total": lucro,
                "quantidade_registros": dados["quantidade_registros"]
            }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular resumo: {str(error)}"
        )

@app.post("/integracao/produtos/sincronizar")
def integrar_produtos(
    limit: int = Query(default=10, ge=1, le=100)
):

    resultado = sincronizar_produtos(limit)

    return resultado

@app.get("/integracao/produtos")
def listar_produtos_integrados(
    limit: int = Query(default=20, ge=1, le=100)
):
    try:

        with engine.connect() as connection:

            result = connection.execute(
                text("""
                    SELECT
                        id,
                        api_id,
                        nome_produto,
                        categoria,
                        marca,
                        preco,
                        estoque,
                        data_integracao,
                        data_atualizacao
                    FROM integracao_produtos
                    ORDER BY id DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )

            produtos = [
                dict(row)
                for row in result.mappings()
            ]

            return {
                "quantidade": len(produtos),
                "dados": produtos
            }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar produtos integrados: {str(error)}"
        )

@app.get("/integracao/logs")
def listar_logs(
    limit: int = Query(default=20, ge=1, le=100)
):
    try:

        with engine.connect() as connection:

            result = connection.execute(
                text("""
                    SELECT
                        id,
                        tipo_integracao,
                        data_inicio,
                        data_fim,
                        status,
                        total_recebido,
                        total_inserido,
                        total_atualizado,
                        total_erros,
                        mensagem
                    FROM log_integracao
                    ORDER BY id DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )

            logs = [
                dict(row)
                for row in result.mappings()
            ]

            return {
                "quantidade": len(logs),
                "dados": logs
            }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar logs: {error}"
        )