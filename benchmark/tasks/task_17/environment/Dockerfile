FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for JavaScript parsing and packages required for attacks
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

# Install Python documentation tools
RUN pip3 install --no-cache-dir \
    flask \
    flask-restful \
    openapi-spec-validator \
    pyyaml

# Install Node.js tools for API documentation
RUN npm install -g swagger-jsdoc swagger-ui-express

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
