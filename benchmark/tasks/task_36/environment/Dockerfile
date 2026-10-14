FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    bash \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.3.2

WORKDIR /app

COPY app /app
COPY tests /tests
RUN chmod +x /tests/test.sh

CMD ["/bin/bash"]
