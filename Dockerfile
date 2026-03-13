FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc ffmpeg libssl-dev libffi-dev ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /ffmpeg_libs && \
    cp /usr/bin/ffmpeg /usr/bin/ffprobe /ffmpeg_libs/ && \
    ldd /usr/bin/ffmpeg | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /ffmpeg_libs/

COPY backend/requirements.txt ./backend/
RUN python -m venv /home/cache-python/tvbox312
ENV PATH="/home/cache-python/tvbox312/bin:$PATH"

RUN pip install --upgrade pip && pip install -r ./backend/requirements.txt

# 第二阶段：运行阶段
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /home/cache-python/tvbox312 /home/cache-python/tvbox312

COPY --from=builder /ffmpeg_libs/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /ffmpeg_libs/ffprobe /usr/bin/ffprobe
COPY --from=builder /ffmpeg_libs/*.so* /usr/lib/x86_64-linux-gnu/
RUN ldconfig

COPY .env .
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY spider/ ./spider/

ENV VIRTUAL_ENV="/home/cache-python/tvbox312"
ENV PATH="/home/cache-python/tvbox312/bin:$PATH"
ENV PYTHONPATH="/app/backend"

EXPOSE 8001
WORKDIR /app/backend
CMD ["gunicorn", "-c", "gunicorn.conf.py", "application:app"]