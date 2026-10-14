#!/usr/bin/env python3
import os
import time
import random
import logging
from flask import Flask, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

SLOW_QUERY_THRESHOLD = int(os.getenv('SLOW_QUERY_THRESHOLD', '5000'))
DB_CONNECTION_POOL_SIZE = int(os.getenv('DB_CONNECTION_POOL_SIZE', '5'))

def simulate_db_query():
    """Simulate slow database query with random delays"""
    # ~30% of queries have significant delays (0.5-3.0s)
    if random.random() < 0.3:
        delay = random.uniform(0.5, 3.0)
        logging.warning(f"Slow query detected, delay: {delay:.2f}s")
        time.sleep(delay)
    else:
        time.sleep(random.uniform(0.05, 0.2))

    return {"id": random.randint(1, 1000), "name": f"User {random.randint(1, 1000)}"}

@app.route('/users/<user_id>')
def get_user(user_id):
    """Get user - intentionally slow with intermittent delays"""
    logging.info(f"Request for user {user_id}")
    result = simulate_db_query()
    result["id"] = user_id
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
