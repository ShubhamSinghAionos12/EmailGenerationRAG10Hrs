import os
import json
import mysql.connector


def get_conn():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )


def log(email_id: int, event: str, level="INFO", payload=None):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            "INSERT INTO logs(email_id, level, event, payload) VALUES (%s, %s, %s, %s)",
            (email_id, level, event, json.dumps(payload) if payload is not None else None)
        )
        c.commit()
