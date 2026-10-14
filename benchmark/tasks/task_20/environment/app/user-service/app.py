#!/usr/bin/env python3
import os
import time
import random
import logging
from flask import Flask, jsonify

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/user-service.log'),
        logging.StreamHandler()
    ]
)

SLOW_QUERY_THRESHOLD = int(os.getenv('SLOW_QUERY_THRESHOLD', '5000'))
DB_CONNECTION_POOL_SIZE = int(os.getenv('DB_CONNECTION_POOL_SIZE', '5'))

# Simulate database connection pool exhaustion
active_connections = 0
MAX_CONNECTIONS = DB_CONNECTION_POOL_SIZE

def simulate_db_query():
    """Simulate slow database query with random delays"""
    global active_connections
    
    if active_connections >= MAX_CONNECTIONS:
        logging.warning("Database connection pool exhausted")
        time.sleep(2)  # Wait for connection
        return None
    
    active_connections += 1
    try:
        # Random delays to simulate database issues
        delay = random.uniform(0.5, 3.0)
        time.sleep(delay)
        
        # 30% failure rate to simulate intermittent issues
        if random.random() < 0.3:
            logging.error("Database query timeout")
            return None
        
        return {"id": random.randint(1, 1000), "name": f"User {random.randint(1, 1000)}"}
    finally:
        active_connections -= 1

@app.route('/users/<user_id>')
def get_user(user_id):
    """Get user - intentionally slow with intermittent failures"""
    logging.info(f"Request for user {user_id}")
    result = simulate_db_query()
    
    if result is None:
        logging.error(f"Failed to get user {user_id}: Database timeout")
        return jsonify({"error": "Database timeout"}), 504
    
    result["id"] = user_id
    logging.info(f"Successfully retrieved user {user_id}")
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "active_connections": active_connections}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
