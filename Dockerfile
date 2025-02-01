FROM python:3.13

COPY app/ /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r app/requirements.txt

COPY log_config.yaml /app

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "127.0.0.1,[::1],172.16.0.0/12", "--log-config", "app/log_config.yaml", "app.main:app"]
EXPOSE 8000