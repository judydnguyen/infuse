FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests flask

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/

CMD ["python", "app.py"]
