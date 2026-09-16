<img width="1100" height="894" alt="image" src="https://github.com/user-attachments/assets/beb802cf-9a02-4fa7-aeda-a8b2c9e147fb" />

# Task API

A minimal FastAPI CRUD API for tasks, backed by PostgreSQL running in Docker.

## What this is

- REST endpoints to create, read, update, and delete tasks (`/tasks`)
- PostgreSQL 16 database running as a Docker container
- Database connection configured via `DATABASE_URL` (see `.env.example`)
- All database code lives in one module: `repository.py`
- On first start the `tasks` table is created and seeded with three example tasks

## Run everything with one command

You need [Docker](https://www.docker.com/). Then:

```bash
cp .env.example .env
docker compose up --build
```

The API is served at `http://localhost:3000` (OpenAPI docs at `/docs`).

> Stop a hand-run Postgres container first if port 5432 is already in use:
> `docker stop taskdb` (or `docker compose down` then `docker compose up`).

## Environment variables

See `.env.example`. Copy it to `.env` before running:

| Variable       | Default value                                    | Meaning                        |
| -------------- | ------------------------------------------------ | ------------------------------ |
| `DATABASE_URL` | `postgres://postgres:dev@localhost:5432/tasks`   | Postgres connection string     |

Inside Docker Compose the app reaches the database by the *service name* `db`
(`postgres://postgres:dev@db:5432/tasks`), not `localhost`.

## Endpoints

| Method   | Path             | Body                  | Status | Description             |
| -------- | ---------------- | --------------------- | ------ | ----------------------- |
| `GET`    | `/tasks`         | —                     | `200`  | List all tasks          |
| `GET`    | `/tasks/{id}`    | —                     | `200`  | Get one task            |
| `GET`    | `/tasks/{id}`    | —                     | `404`  | Unknown id → `{"error": "Task not found"}` |
| `POST`   | `/tasks`         | `{"title": "..."}`    | `201`  | Create a task           |
| `POST`   | `/tasks`         | missing/blank title   | `400`  | `{"error": "title is required"}` |
| `PUT`    | `/tasks/{id}`    | `{"done": true}` or `{"title": "..."}` | `200` | Update a task |
| `PUT`    | `/tasks/{id}`    | —                     | `404`  | Unknown id |
| `DELETE` | `/tasks/{id}`    | —                     | `204`  | Delete a task (empty body) |
| `DELETE` | `/tasks/{id}`    | —                     | `404`  | Unknown id |

## Example

```bash
$ curl -i http://localhost:3000/tasks
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"title":"Do the dishes","done":false},{"id":2,"title":"Walk the dog","done":false},{"id":3,"title":"Buy groceries","done":false}]
```

## Data in the database

```bash
$ docker compose exec db psql -U postgres -d tasks -c '\dt' -c 'SELECT * FROM tasks;'
        List of relations
 Schema |  Name  | Type  | Owner
--------+--------+-------+-------
 public | tasks  | table | postgres
(1 row)

 id |     title      | done
----+----------------+------
  1 | Do the dishes  | f
  2 | Walk the dog   | f
  3 | Buy groceries  | f
(3 rows)
```

The database is stored in the named volume `taskdata`, so your tasks survive
`docker compose down` and come back on `docker compose up --build`.