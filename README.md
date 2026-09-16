<img width="1100" height="894" alt="image" src="https://github.com/user-attachments/assets/beb802cf-9a02-4fa7-aeda-a8b2c9e147fb" />

# Task API

FastAPI CRUD API for tasks.

## Run the database (Postgres 18) with Docker

```bash
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks \
  -p 5432:5432 -v taskdata:/var/lib/postgresql -d postgres
```

- Container name: `taskdb`
- Password: `dev`
- Database: `tasks`
- Port: `5432`
- Data persists in the named Docker volume `taskdata`

## Checkpoint

Verify the container is running and open psql:

```bash
docker ps
docker exec -it taskdb psql -U postgres -d tasks
```