#!/usr/bin/env python3
import os
import requests
import time
import logging
from flask import Flask, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', '1000'))
MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', '10'))
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user-service:5000')

# No connection pooling, no retry logic, no circuit breaker
session = requests.Session()
session.max_connections = MAX_CONNECTIONS

def validate_user(user_id):
    """Validate user - intentionally unoptimized with no timeout handling"""
    try:
        # No timeout specified, no retry, no circuit breaker
        response = session.get(f'{USER_SERVICE_URL}/users/{user_id}')
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"Connection timeout to user-service for user {user_id}")
        return {"error": "Timeout"}, 504
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error to user-service: {e}")
        return {"error": "Connection failed"}, 503
    except Exception as e:
        logging.error(f"Error validating user {user_id}: {e}")
        return {"error": str(e)}, 500

@app.route('/auth/validate/<user_id>')
def auth_validate(user_id):
    result = validate_user(user_id)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Simulate rapid calls that will cause connection pool exhaustion
    import threading
    
    def stress_test():
        time.sleep(2)  # Wait for services to start
        for i in range(100):
            try:
                validate_user(i % 50)
            except:
                pass
            time.sleep(0.01)
    
    threading.Thread(target=stress_test, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
