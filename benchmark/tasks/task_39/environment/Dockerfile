FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    bash \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app /app
COPY tests /tests
RUN chmod +x /app/scripts/deploy_check.sh /tests/test.sh

CMD ["/bin/bash"]
