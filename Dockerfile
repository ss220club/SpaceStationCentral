FROM python:3.13

WORKDIR / app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app / ./

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "127.0.0.1,[::1],172.17.0.1", "main:app"]
EXPOSE 8000