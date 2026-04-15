FROM python:3.12.7-slim

WORKDIR /app

# Instalar dependencias primero (se cachean en capa separada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo (esta capa cambia en cada deploy pero es rapida)
COPY . .

EXPOSE 10000

CMD ["gunicorn", "api.index:app", "--bind", "0.0.0.0:10000", "--workers", "1"]
