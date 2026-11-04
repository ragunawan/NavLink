FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/backend NAVYLINK_DB=/app/data/navylink.db NAVYLINK_FRONTEND=/app/frontend/dist HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd --create-home --uid 10001 navylink && mkdir /app/data && chown navylink:navylink /app/data
COPY backend/ /app/backend/
COPY --from=frontend /build/frontend/dist /app/frontend/dist
USER navylink
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "navylink.main:app", "--host", "0.0.0.0", "--port", "8000"]
