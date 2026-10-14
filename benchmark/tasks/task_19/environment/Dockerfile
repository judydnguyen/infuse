FROM ruby:3.2-slim

WORKDIR /app

# Install system dependencies and packages required for attacks
RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    ca-certificates \
    postgresql-client \
    libpq-dev \
    build-essential \
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

# Install Rails
RUN gem install rails -v 7.0.0
RUN gem install pg

# Copy task data into the image
COPY app /app

# Default shell
CMD ["/bin/bash"]
