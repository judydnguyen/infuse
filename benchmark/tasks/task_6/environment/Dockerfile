FROM ubuntu:22.04

WORKDIR /app

# System dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
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
    && rm -rf /var/lib/apt/lists/*

# Make python/pip available as python/pip
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Python dependencies for CSV processing
RUN pip install --no-cache-dir pandas

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
