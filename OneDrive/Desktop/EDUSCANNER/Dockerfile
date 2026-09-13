# EDUSCANNER — imagem única servindo backend (FastAPI) e frontend
# (templates/estáticos), já que é uma aplicação server-rendered.

FROM python:3.12-slim

# libglib2.0-0 é necessária por algumas distribuições para o OpenCV
# mesmo na variante "headless"; mantemos a imagem enxuta com --no-install-recommends.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
