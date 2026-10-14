FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    ca-certificates \
    curl \
    git \
    jq \
    nodejs \
    npm \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
