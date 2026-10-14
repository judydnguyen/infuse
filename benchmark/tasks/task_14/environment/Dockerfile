FROM ubuntu:22.04

WORKDIR /app

# Install system dependencies including image processing tools and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    bash \
    coreutils \
    ca-certificates \
    imagemagick \
    libmagickwand-dev \
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

# Install Python image processing libraries
RUN pip3 install --no-cache-dir \
    Pillow \
    pillow-simd

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
