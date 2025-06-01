# This is the Inventory service: it receives package requests from the CRM.

from flask import Flask, request, jsonify
from flasgger import Swagger
import threading
import logging

app = Flask(__name__)
app.config['SWAGGER'] = {
    'title': 'Inventory API',
    'uiversion': 3,
    'openapi': '3.0.2',
    'specs_route': "/docs/"
}
Swagger(app)

logging.basicConfig(level=logging.INFO)

# In-memory store for package requests
packages = {}
next_pid = 1
lock = threading.Lock()

@app.route('/health')
def health():
    # Simple health check
    return {"status": "Inventory running"}, 200

@app.route('/package_requests', methods=['POST'])
def create_package():
    """
Create a welcome package
---
tags:
  - Inventory
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required:
          - customer_id
          - package_type
        properties:
          customer_id:
            type: integer
          package_type:
            type: string
responses:
  201:
    description: Package request created
  400:
    description: Missing fields
    """
    global next_pid
    data = request.get_json()
    if not data or 'customer_id' not in data or 'package_type' not in data:
        return {"error": "Missing fields"}, 400

    # Assign a new package request ID
    with lock:
        pid = next_pid
        next_pid += 1
        packages[pid] = {
            "id": pid,
            "customer_id": data["customer_id"],
            "package_type": data["package_type"],
            "status": "received"
        }

    return jsonify(packages[pid]), 201

@app.route('/package_requests', methods=['GET'])
def list_packages():
    """
List all package requests
---
tags:
  - Inventory
responses:
  200:
    description: All package requests
    content:
      application/json:
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              customer_id:
                type: integer
              package_type:
                type: string
              status:
                type: string
    """
    return jsonify(list(packages.values())), 200

if __name__ == '__main__':
    # Run the Inventory service on port 5001
    app.run(host="0.0.0.0", port=5001)
