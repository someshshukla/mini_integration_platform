import logging
import threading
import time
import requests
from flask import Flask, request, jsonify
from flasgger import Swagger

app = Flask(__name__)

app.config['SWAGGER'] = {
    'title': 'Mini Integration Platform API - Dev Version',
    'uiversion': 3,
    'openapi': '3.0.2',
    'specs_route': "/api/docs/"
}
swagger = Swagger(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

customers_db = {}
package_requests_db = {}
next_customer_id_counter = 1
next_package_request_id_counter = 1

db_lock = threading.Lock()

INVENTORY_SERVICE_URL = "http://127.0.0.1:5000/package_requests"

MAX_INTEGRATION_ATTEMPTS = 3
INTEGRATION_RETRY_WAIT_SECONDS = 2

def get_new_id_for(resource_type_key):
    global next_customer_id_counter, next_package_request_id_counter
    new_id = -1
    with db_lock:
        if resource_type_key == 'customer':
            new_id = next_customer_id_counter
            next_customer_id_counter += 1
        elif resource_type_key == 'package_request':
            new_id = next_package_request_id_counter
            next_package_request_id_counter += 1
    return new_id

@app.route('/customers', methods=['POST'])
def handle_add_customer_request():
    """
    ---
    tags:
      - CRM
    requestBody:
      description: Customer details
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name, email]
            properties:
              name: {type: string, example: "Human User"}
              email: {type: string, format: email, example: "human@example.com"}
    responses:
      201:
        description: Customer added. Check 'integration_status' for package request outcome.
        content:
          application/json:
            schema:
              type: object
              properties:
                id: {type: integer}
                name: {type: string}
                email: {type: string}
                integration_status: {type: string}
      400:
        description: Bad request (e.g., missing fields)
    """
    logging.info("Received request to add a new customer.")
    try:
        customer_payload = request.get_json()
        if not customer_payload:
            logging.warning("Empty JSON payload received for add customer.")
            return jsonify({"error": "Request body must be JSON and not empty"}), 400
    except Exception as e:
        logging.error(f"Could not parse JSON for add customer: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400

    customer_name = customer_payload.get('name')
    customer_email = customer_payload.get('email')

    if not customer_name or not customer_email:
        missing = []
        if not customer_name: missing.append('name')
        if not customer_email: missing.append('email')
        logging.warning(f"Missing fields for add customer: {', '.join(missing)}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    new_customer_id = get_new_id_for('customer')
    new_customer_record = {
        "id": new_customer_id,
        "name": customer_name,
        "email": customer_email
    }

    with db_lock:
        customers_db[new_customer_id] = new_customer_record
    logging.info(f"CRM: Successfully added customer {new_customer_id}: {customer_name}")

    integration_outcome_message = "Integration not attempted yet."
    package_details_for_inventory = {
        "customer_id": new_customer_id,
        "package_type": "welcome"
    }

    current_attempt = 0
    inventory_call_succeeded = False
    while current_attempt < MAX_INTEGRATION_ATTEMPTS:
        current_attempt += 1
        logging.info(f"Integration: Attempt {current_attempt}/{MAX_INTEGRATION_ATTEMPTS} to create package request for customer {new_customer_id}")
        try:
            inventory_response = requests.post(INVENTORY_SERVICE_URL, json=package_details_for_inventory, timeout=5)
            inventory_response.raise_for_status()
            inventory_call_succeeded = True
            integration_outcome_message = f"Package request created successfully for customer {new_customer_id} on attempt {current_attempt}."
            logging.info(integration_outcome_message)
            break
        except requests.exceptions.Timeout:
            logging.warning(f"Integration Error (Attempt {current_attempt}): Timeout calling inventory service for customer {new_customer_id}.")
            integration_outcome_message = f"Attempt {current_attempt} timed out."
        except requests.exceptions.ConnectionError:
            logging.warning(f"Integration Error (Attempt {current_attempt}): Connection error to inventory service for customer {new_customer_id}.")
            integration_outcome_message = f"Attempt {current_attempt} had connection error."
        except requests.exceptions.HTTPError as http_err:
            logging.warning(f"Integration Error (Attempt {current_attempt}): Inventory service returned HTTP {http_err.response.status_code} for customer {new_customer_id}.")
            integration_outcome_message = f"Attempt {current_attempt} failed with HTTP {http_err.response.status_code} from inventory."
        except requests.exceptions.RequestException as e:
            logging.warning(f"Integration Error (Attempt {current_attempt}): Generic request exception for customer {new_customer_id}. Error: {e}")
            integration_outcome_message = f"Attempt {current_attempt} had a general request error."

        if not inventory_call_succeeded and current_attempt < MAX_INTEGRATION_ATTEMPTS:
            logging.info(f"Will retry inventory call in {INTEGRATION_RETRY_WAIT_SECONDS} seconds...")
            time.sleep(INTEGRATION_RETRY_WAIT_SECONDS)
        elif not inventory_call_succeeded and current_attempt >= MAX_INTEGRATION_ATTEMPTS:
            integration_outcome_message = f"Failed to create package request for customer {new_customer_id} after {MAX_INTEGRATION_ATTEMPTS} attempts. Last error: {integration_outcome_message}"
            logging.error(integration_outcome_message)

    response_to_client = new_customer_record.copy()
    response_to_client["integration_status"] = integration_outcome_message
    return jsonify(response_to_client), 201

@app.route('/customers', methods=['GET'])
def list_all_customers():
    """
    ---
    tags: [CRM]
    responses:
      200:
        description: A list of customers.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id: {type: integer}
                  name: {type: string}
                  email: {type: string}
    """
    logging.debug("Request to list all customers.")
    all_customers = []
    with db_lock:
        for cust_record in customers_db.values():
            all_customers.append(cust_record)
    return jsonify(all_customers), 200

@app.route('/package_requests', methods=['POST'])
def handle_create_package_request():
    """
    ---
    tags: [Inventory]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [customer_id, package_type]
            properties:
              customer_id: {type: integer, example: 1}
              package_type: {type: string, example: "welcome_pack_v1"}
    responses:
      201:
        description: Package request logged.
      400:
        description: Missing data.
    """
    package_data = request.get_json()
    if not package_data or not package_data.get('customer_id') or not package_data.get('package_type'):
        return jsonify({"error": "customer_id and package_type are required"}), 400

    req_id = get_new_id_for('package_request')
    new_package_req = {
        "id": req_id,
        "customer_id": package_data["customer_id"],
        "package_type": package_data["package_type"],
        "status": "received"
    }
    with db_lock:
        package_requests_db[req_id] = new_package_req
    logging.info(f"Inventory: Created package request {req_id} for customer {package_data['customer_id']}")
    return jsonify(new_package_req), 201

@app.route('/package_requests', methods=['GET'])
def list_all_package_requests():
    """
    ---
    tags: [Inventory]
    responses:
      200:
        description: All package requests.
    """
    return jsonify(list(package_requests_db.values())), 200

if __name__ == '__main__':
    print("Starting the Mini Integration Platform server...")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)