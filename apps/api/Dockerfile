FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/packages:/app/apps/api

WORKDIR /app

COPY packages ./packages
COPY apps/api ./apps/api
COPY apps/streamlit/logo.png ./apps/streamlit/logo.png
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e packages -e apps/api

WORKDIR /app/apps/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
