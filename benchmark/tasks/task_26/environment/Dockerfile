FROM python:3.10-slim

WORKDIR /app

COPY app /app
COPY tests /tests
RUN chmod +x /tests/test.sh

CMD ["/bin/bash"]
