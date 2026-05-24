FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

RUN sed -i "s@deb.debian.org@mirrors.aliyun.com@g" /etc/apt/sources.list.d/debian.sources && \
    sed -i "s@security.debian.org@mirrors.aliyun.com@g" /etc/apt/sources.list.d/debian.sources

RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip curl gcc libssl-dev ca-certificates && \
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh && \
    echo "=== 检查 deno ===" && deno --version && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN python -m venv /home/cache-python/tvbox312
ENV PATH="/home/cache-python/tvbox312/bin:$PATH"

RUN pip install --upgrade pip && pip install -r ./backend/requirements.txt

# 第二阶段：运行阶段
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /home/cache-python/tvbox312 /home/cache-python/tvbox312
COPY --from=builder /usr/local/bin/deno /usr/local/bin/deno

COPY .env .
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY spider/ ./spider/

ENV VIRTUAL_ENV="/home/cache-python/tvbox312"
ENV PATH="/home/cache-python/tvbox312/bin:/usr/local/bin:$PATH"
ENV PYTHONPATH="/app/backend"

EXPOSE 8001
WORKDIR /app/backend
CMD ["gunicorn", "-c", "gunicorn.conf.py", "application:app"]