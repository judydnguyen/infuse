FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl git jq sqlite3 tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app /app
RUN pip install --no-cache-dir -r requirements.txt
COPY tests /tests
RUN chmod +x /tests/test.sh

CMD ["/bin/bash"]
