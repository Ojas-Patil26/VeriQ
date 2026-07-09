FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# python api.py honors the PORT env var Railway injects (defaults to 8080).
CMD ["python", "api.py"]
