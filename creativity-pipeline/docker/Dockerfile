# Creativity Pipeline Docker Image
# Multi-stage build for smaller image size

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set timezone
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install runtime dependencies and supercronic
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic for cron scheduling
ARG SUPERCRONIC_VERSION=v0.2.29
ARG TARGETARCH
RUN case "${TARGETARCH}" in \
        "amd64") SUPERCRONIC_ARCH="linux-amd64" ;; \
        "arm64") SUPERCRONIC_ARCH="linux-arm64" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-${SUPERCRONIC_ARCH}" \
    -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic

# Create non-root user
RUN useradd -m -u 1000 pipeline

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/pipeline/.local
ENV PATH=/home/pipeline/.local/bin:$PATH

# Copy application code
COPY --chown=pipeline:pipeline src/ /app/src/
COPY --chown=pipeline:pipeline config/ /app/config/

# Create directories
RUN mkdir -p /app/logs /vault && chown -R pipeline:pipeline /app /vault

# Copy entrypoint
COPY --chown=pipeline:pipeline docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy crontab
COPY --chown=pipeline:pipeline docker/crontab /app/crontab

# Switch to non-root user
USER pipeline

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV VAULT_PATH=/vault

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["scheduler"]
