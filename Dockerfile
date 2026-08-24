FROM python:3.12-slim

WORKDIR /srv/kafkaforge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV APP_PORT=8080
EXPOSE 8080

RUN useradd --create-home --uid 1000 kafkaforge
USER kafkaforge

CMD ["python", "-m", "app.main"]
