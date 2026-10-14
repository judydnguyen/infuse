#!/usr/bin/env python3
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/products/<product_id>')
def get_product(product_id):
    return jsonify({"id": product_id, "name": "Product"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
