from flask import Flask, request, jsonify
import requests
import threading
import time
import logging
from flasgger import Swagger

app = Flask(__name__)
app.config['SWAGGER'] = {
    'title': 'CRM API',
    'uiversion': 3,
    'openapi': '3.0.2',
    'specs_route': "/docs/"
}
Swagger(app)

logging.basicConfig(level=logging.INFO)

# In-memory store for customers
customers = {}
next_id = 1
lock = threading.Lock()

# URL of the Inventory service
INVENTORY_URL = "http://inventory:5001/package_requests"

@app.route('/health')
def health():
    # Simple health check
    return {"status": "CRM running"}, 200

@app.route('/customers', methods=['POST'])
def create_customer():
    """
Create a new customer, then request a welcome package.
---
tags:
  - CRM
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required:
          - name
          - email
        properties:
          name:
            type: string
            example: "John Doe"
          email:
            type: string
            format: email
            example: "john@example.com"
responses:
  201:
    description: Customer created (integration_status shows if Inventory succeeded)
  400:
    description: Missing fields
    """
    global next_id
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return {"error": "Missing fields"}, 400

    # Assign a new customer ID
    with lock:
        cid = next_id
        next_id += 1
        customers[cid] = {"id": cid, "name": data['name'], "email": data['email']}

    # Attempt to send a welcome-package request up to 3 times
    payload = {"customer_id": cid, "package_type": "welcome"}
    success = False
    for _ in range(3):
        try:
            r = requests.post(INVENTORY_URL, json=payload, timeout=3)
            if r.status_code == 201:
                success = True
                break
        except Exception as e:
            logging.warning("Retrying due to error: %s", e)
            time.sleep(1)

    # Record integration status in the customer record
    customers[cid]["integration_status"] = "success" if success else "failed"
    return jsonify(customers[cid]), 201

@app.route('/customers', methods=['GET'])
def list_customers():
    """
List all customers
---
tags:
  - CRM
responses:
  200:
    description: List of customers
    content:
      application/json:
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              email:
                type: string
              integration_status:
                type: string
    """
    return jsonify(list(customers.values())), 200

if __name__ == '__main__':
    # Run the CRM service on port 5000
    app.run(host="0.0.0.0", port=5000)