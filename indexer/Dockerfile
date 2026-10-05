FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY indexer/requirements.txt .
RUN pip install -r requirements.txt
COPY indexer/main.py .
CMD ["python", "main.py"]
