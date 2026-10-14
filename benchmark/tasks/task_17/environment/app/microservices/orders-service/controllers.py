from flask import Flask, request, jsonify
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class OrderList(Resource):
    """
    Orders Collection
    GET /api/orders - List all orders
    POST /api/orders - Create new order
    """
    def get(self):
        """
        List orders
        Query params:
        - status: filter by status (pending|completed|cancelled)
        - user_id: filter by user
        - start_date: filter from date (ISO format)
        - end_date: filter to date (ISO format)
        """
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        return {
            'orders': [],
            'total': 0
        }
    
    def post(self):
        """
        Create order
        Body:
        - user_id: string (required)
        - items: array of {product_id, quantity, price}
        - shipping_address: object
        Returns: Created order with order_id
        """
        data = request.get_json()
        return {
            'order_id': 'ORD-12345',
            'status': 'pending',
            'total': 0,
            'created_at': '2024-02-01T10:00:00Z'
        }, 201

class Order(Resource):
    """
    Single Order
    GET /api/orders/<order_id> - Get order details
    PUT /api/orders/<order_id> - Update order
    DELETE /api/orders/<order_id> - Cancel order
    """
    def get(self, order_id):
        """Get order by ID"""
        return {
            'order_id': order_id,
            'user_id': 'user-123',
            'status': 'completed',
            'items': [],
            'total': 299.99
        }
    
    def put(self, order_id):
        """Update order status"""
        data = request.get_json()
        return {'success': True}
    
    def delete(self, order_id):
        """Cancel order (soft delete)"""
        return {'cancelled': True}

api.add_resource(OrderList, '/api/orders')
api.add_resource(Order, '/api/orders/<string:order_id>')
