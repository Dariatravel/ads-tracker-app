FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV ADS_TRACKER_DATA_DIR=/data

COPY app.py README.md /app/

EXPOSE 8080

CMD ["sh", "-c", "mkdir -p \"$ADS_TRACKER_DATA_DIR\" && python app.py --host 0.0.0.0 --port ${PORT:-8080}"]
