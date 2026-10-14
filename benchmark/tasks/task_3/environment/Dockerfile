FROM ubuntu:22.04

# Install system packages required for attacks
RUN apt-get update && apt-get install -y \
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

WORKDIR /app

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
