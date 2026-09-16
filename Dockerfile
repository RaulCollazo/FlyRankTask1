FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir "fastapi[standard]>=0.141.1" "psycopg[binary]" python-dotenv
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]