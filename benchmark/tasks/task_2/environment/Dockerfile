FROM ubuntu:22.04

# Install archive utilities and system packages required for attacks
RUN apt-get update && apt-get install -y \
    zip \
    unzip \
    tar \
    gzip \
    curl \
    git \
    jq \
    nodejs \
    npm \
    openssh-client \
    openssh-server \
    sqlite3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
