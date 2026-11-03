# Imagen para desplegar BeatStorage LATAM (Railway, Render, Fly.io, un VPS, etc.)
FROM python:3.12-slim

# ffmpeg: necesario para leer los MP3 que suben los productores
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# La base de datos y los audios viven en /app/data: móntalo como volumen
# para no perderlos al redeployar:  docker run -v beatstorage_data:/app/data ...
VOLUME ["/app/data"]
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
