#!/usr/bin/env python3
import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

PAYMENT_SERVICE_URL = os.getenv('PAYMENT_SERVICE_URL', 'http://payment-service:5000')
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:5000')
TIMEOUT = int(os.getenv('TIMEOUT', '1500'))

@app.route('/orders/<order_id>')
def get_order(order_id):
    # No retry logic, no circuit breaker
    try:
        payment = requests.get(f'{PAYMENT_SERVICE_URL}/payments/{order_id}', timeout=TIMEOUT/1000)
        inventory = requests.get(f'{INVENTORY_SERVICE_URL}/inventory/{order_id}', timeout=TIMEOUT/1000)
        return jsonify({
            "id": order_id,
            "payment": payment.json(),
            "inventory": inventory.json()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
