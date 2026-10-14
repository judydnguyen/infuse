FROM python:3.10-slim

RUN pip install --no-cache-dir pyyaml==6.0.2

WORKDIR /app

COPY app /app
COPY tests /tests
RUN chmod +x /tests/test.sh

CMD ["/bin/bash"]
