FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema para compilar psycopg2-binary
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

RUN pip install python-dotenv

COPY requirements.txt /app/
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

RUN useradd -m devuser && \
    chown -R devuser:devuser /app

USER devuser

ENV PYTHONPATH=/app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8084", "--reload"]