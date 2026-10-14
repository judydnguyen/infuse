FROM python:3.10-slim

# Install system packages required for attacks
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    nodejs \
    npm \
    vim \
    nano \
    zip \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy task data into the image
COPY app /app

# Copy test script to /tests (accessible as /app/../tests/test.sh)
COPY tests /tests

# Make test script executable
RUN chmod +x /tests/test.sh

# Default shell
CMD ["/bin/bash"]