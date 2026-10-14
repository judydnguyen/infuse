FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    bash \
    grep \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app /app
COPY tests /tests
RUN chmod +x /tests/test.sh

CMD ["/bin/bash"]
