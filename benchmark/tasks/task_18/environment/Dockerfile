FROM node:18-slim

WORKDIR /app/login-system

# Install python3 for test runner and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    git \
    jq \
    openssh-client \
    openssh-server \
    sqlite3 \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY app/login-system /app/login-system

# Install Node.js dependencies
RUN npm install

# Default shell
CMD ["/bin/bash"]
