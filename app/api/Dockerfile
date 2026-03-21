FROM python:3.11-slim

WORKDIR /app

# Install only API dependencies (NO ML libraries here)
COPY app/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/api /app

EXPOSE 8000

# Thin entrypoint: no ML / full-repo imports (see main_k8s.py). Use main:app only with full project layout + deps.
CMD ["uvicorn", "main_k8s:app", "--host", "0.0.0.0", "--port", "8000"]
