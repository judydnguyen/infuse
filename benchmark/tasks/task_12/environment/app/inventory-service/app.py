#!/usr/bin/env python3
import os
import time
import random
from flask import Flask, jsonify

app = Flask(__name__)

DB_QUERY_TIMEOUT = int(os.getenv('DB_QUERY_TIMEOUT', '3000'))
CONNECTION_POOL_SIZE = int(os.getenv('CONNECTION_POOL_SIZE', '3'))

@app.route('/inventory/<item_id>')
def get_inventory(item_id):
    # Simulate slow database query
    time.sleep(DB_QUERY_TIMEOUT / 1000 + random.uniform(0, 1))
    if random.random() < 0.2:
        return jsonify({"error": "Query timeout"}), 504
    return jsonify({"id": item_id, "stock": random.randint(0, 100)})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
