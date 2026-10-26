FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV PYTHONPATH=/app PROCESSING_MODE=LOCAL
EXPOSE 8000
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]
