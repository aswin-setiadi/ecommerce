FROM python:3.11-slim
RUN apt-get update && apt-get install -y netcat-traditional

WORKDIR /app
COPY requirements.txt run.sh .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["tail", "-f", "/dev/null"]
CMD ["./run.sh", "kafka", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
