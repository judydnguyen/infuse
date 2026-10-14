FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    ca-certificates \
    cron \
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

# Install Python web scraping libraries
RUN pip3 install --no-cache-dir \
    requests \
    beautifulsoup4 \
    lxml \
    html5lib \
    selenium \
    pandas

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
