FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements_production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p templates static logs

ENV FLASK_APP=app_production.py
ENV FLASK_ENV=production
ENV PORT=8080

EXPOSE 8080

CMD gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 4 --timeout 300 --access-logfile - --error-logfile -