#!/usr/bin/env python3
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/<path:path>', methods=['GET', 'POST'])
def gateway(path):
    # Simple gateway without proper routing or circuit breakers
    service_map = {
        'auth': 'http://auth-service:5000',
        'users': 'http://user-service:5000',
        'products': 'http://product-service:5000',
        'orders': 'http://order-service:5000',
    }
    
    service = path.split('/')[0]
    if service in service_map:
        try:
            url = f"{service_map[service]}/{path}"
            response = requests.get(url, timeout=2)
            return jsonify(response.json()), response.status_code
        except Exception as e:
            return jsonify({"error": str(e)}), 503
    
    return jsonify({"error": "Service not found"}), 404

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
