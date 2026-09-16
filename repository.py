import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


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


def get_tasks():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
            return cur.fetchall()


def get_task(task_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s",
                (task_id,),
            )
            return cur.fetchone()


def create_task(title):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                (title, False),
            )
            return cur.fetchone()


def update_task(task_id, title=None, done=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            sets, values = [], []
            if title is not None:
                sets.append("title = %s")
                values.append(title)
            if done is not None:
                sets.append("done = %s")
                values.append(done)
            values.append(task_id)
            cur.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE id = %s RETURNING id, title, done",
                values,
            )
            return cur.fetchone()


def delete_task(task_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0