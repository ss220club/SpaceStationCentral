FROM python:3.13-slim

# Install UV first for better layer caching
RUN pip install --no-cache-dir uv

RUN mkdir -p /srv/ssc
WORKDIR /srv/ssc
COPY . .

RUN uv sync

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "127.0.0.1,[::1],172.16.0.0/12", "--log-config", "log_config.yaml", "app.main:app"]
EXPOSE 8000
