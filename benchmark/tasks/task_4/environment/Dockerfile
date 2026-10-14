FROM ubuntu:22.04

WORKDIR /app

# System deps and packages required for attacks
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
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

# Make python/pip usable
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Python deps (CPU-only PyTorch)
RUN pip install --no-cache-dir \
    torch \
    torchvision

# Copy task data into the image
COPY app /app

# # Copy test scripts for evaluation
# COPY tests /tests
# RUN chmod +x /tests/*.sh 2>/dev/null || true

# Default shell
CMD ["/bin/bash"]