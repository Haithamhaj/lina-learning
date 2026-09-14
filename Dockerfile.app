# Multi-stage build for Lina Application (Next.js Standalone + FastAPI + Supervisor)
FROM node:20-slim AS node-builder

WORKDIR /app

COPY . .

RUN npm ci --include=dev

# Environment variables for Next.js build
ARG CLERK_PUBLISHABLE_KEY=pk_test_ZmluZS1raWQtOTk3OS5jbGVyay5hY2NvdW50cy5kZXYk
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
ENV CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY

# Build Next.js web application
RUN npm --prefix apps/web run build

# Final runtime image with Python 3.11 + Node 20
FROM python:3.11-slim

WORKDIR /app

# Install Node.js & build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements (including CPU PyTorch for Docling)
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/api/production-constraints.txt /app/apps/api/production-constraints.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r apps/api/requirements.txt -c apps/api/production-constraints.txt

# Copy repository code
COPY . /app

# Copy built Next.js standalone output & assets
COPY --from=node-builder /app/apps/web/.next /app/apps/web/.next
COPY --from=node-builder /app/apps/web/.next/static /app/apps/web/.next/standalone/apps/web/.next/static
COPY --from=node-builder /app/apps/web/public /app/apps/web/.next/standalone/apps/web/public
COPY --from=node-builder /app/apps/web/.next/static /app/.next/static
COPY --from=node-builder /app/apps/web/public /app/public
COPY --from=node-builder /app/node_modules /app/node_modules
COPY --from=node-builder /app/apps/web/public /app/apps/web/public

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=5000
ENV API_HOST=127.0.0.1
ENV API_PORT=8000
ENV LINA_PRODUCTION_PYTHON=python
ENV LINA_ENABLE_WORKER=false
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "scripts/production_supervisor.py"]
