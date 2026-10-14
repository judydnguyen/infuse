#!/usr/bin/env python3
import os
import time
import random
from flask import Flask, jsonify

app = Flask(__name__)

PROCESSING_DELAY = int(os.getenv('PROCESSING_DELAY', '2000'))
MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', '5'))

active_requests = 0

@app.route('/payments/<payment_id>')
def get_payment(payment_id):
    global active_requests
    if active_requests >= MAX_CONCURRENT:
        return jsonify({"error": "Service overloaded"}), 503
    
    active_requests += 1
    try:
        time.sleep(PROCESSING_DELAY / 1000 + random.uniform(0, 1))
        return jsonify({"id": payment_id, "status": "processed"})
    finally:
        active_requests -= 1

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
