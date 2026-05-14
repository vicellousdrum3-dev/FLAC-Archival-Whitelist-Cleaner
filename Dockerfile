FROM python:3.12-alpine

RUN apk add --no-cache \
    flac \
    coreutils \
    grep \
    sed \
    gawk \
    zip \
    unzip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY flac_archival_whitelist_recursive.sh .
RUN chmod +x /app/flac_archival_whitelist_recursive.sh

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
