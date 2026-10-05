FROM python:3.12-slim
WORKDIR /app
COPY indexer/requirements.txt .
RUN pip install -r requirements.txt
COPY indexer/main.py .
CMD ["python", "main.py"]
