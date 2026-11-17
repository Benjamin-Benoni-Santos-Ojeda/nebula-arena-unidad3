FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
USER 1000
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --threads 4 main:app"]

