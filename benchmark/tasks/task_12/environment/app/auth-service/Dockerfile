FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests flask

COPY app.py /app/
COPY requirements.txt /app/

CMD ["python", "app.py"]
