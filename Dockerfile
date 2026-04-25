FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client for migration check
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run migrations then start
CMD ["sh", "-c", "python -m alembic upgrade head 2>/dev/null || true && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
