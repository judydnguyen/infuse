FROM ubuntu:22.04

WORKDIR /app

# Install system dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    bash \
    coreutils \
    ca-certificates \
    file \
    curl \
    git \
    jq \
    nodejs \
    npm \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
