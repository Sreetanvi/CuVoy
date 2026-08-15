# Build from repo root: docker build -f backend/Dockerfile .
# Render uses native Python (render.yaml), not this image.

FROM python:3.12-slim

WORKDIR /repo
COPY packages/contracts/python /repo/packages/contracts/python
COPY backend /repo/backend

WORKDIR /repo/backend
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
