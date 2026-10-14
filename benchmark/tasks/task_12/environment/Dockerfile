FROM ubuntu:22.04

WORKDIR /app

# Install system dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    git \
    jq \
    nodejs \
    npm \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    bash \
    coreutils \
    ca-certificates \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for log analysis
RUN pip3 install --no-cache-dir \
    requests \
    flask \
    pyyaml

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
