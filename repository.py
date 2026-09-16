import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id serial PRIMARY KEY,
                    title text,
                    done boolean
                )
                """
            )
            cur.execute("SELECT COUNT(*) FROM tasks")
            empty = cur.fetchone()[0] == 0
            if empty:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Do the dishes", False),
                        ("Walk the dog", False),
                        ("Buy groceries", False),
                    ],
                )