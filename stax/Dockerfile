FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stax/ stax/
COPY scripts/ scripts/

# Phase 0 containers only read public APIs and write to /app/data.
CMD ["python", "scripts/collect.py"]
