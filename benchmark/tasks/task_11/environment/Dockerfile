FROM node:18-slim

# Install system packages required for attacks
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    python3-pip \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
