from pymysql import connect
from pymysql.connections import Connection

from gork_bot.db_service import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def db_connect() -> Connection:
    return connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )


def run_query(
    query: str, params: tuple = (), connection: Connection | None = None
) -> list[tuple]:
    db_connection: Connection = connection if connection else db_connect()
    try:
        with db_connection.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
            db_connection.commit()
            return result
    finally:
        if connection is None:
            db_connection.close()
