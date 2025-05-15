# Mini Integration Platform

A lightweight integration between a mock CRM and a mock Inventory system. When a new customer is added in the CRM, a "welcome package" request is created in the Inventory system.

## Core Features

*   **Mock CRM API:** Add and view customers.
*   **Mock Inventory API:** Create and list package requests.
*   **Integration Logic:** Customer creation in CRM triggers a package request in Inventory, with retries on failure.

## Running the Application

### Prerequisites
*   Python 3.7+
*   pip
*   Docker (Optional)

### Option 1: Local Python
1.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python app.py
    ```
    The app will be available at `http://127.0.0.1:5000`.

### Option 2: Docker
1.  Build the Docker image:
    ```bash
    docker build -t mini-integ .
    ```
2.  Run the container:
    ```bash
    docker run -p 5000:5000 mini-integ
    ```
    The app will be available at `http://127.0.0.1:5000`.

## API Documentation

The application runs on `http://127.0.0.1:5000`.
An interactive Swagger UI is available at: `http://127.0.0.1:5000/api/docs/`

### CRM API

#### 1. Add Customer
*   `POST /customers`
*   **Request Body (JSON):**
    ```json
    {
        "name": "Somesh Shukla",
        "email": "orionbee13@gmail.com"
    }
    ```
    *Requires `name` and `email`.*
*   **Success Response (201 Created):**
    ```json
    {
        "id": 1,
        "name": "Somesh Shukla",
        "email": "orionbee13@gmail.com",
        "integration_status": "Package request created successfully..." // Or failure message
    }
    ```
*   **Error Response (400 Bad Request):**
    ```json
    { "error": "Missing required fields: email" }
    ```

#### 2. View Customers
*   `GET /customers`
*   **Success Response (200 OK):**
    ```json
    [
        { "id": 1, "name": "Somesh Shukla", "email": "orionbee13@gmail.com" }
    ]
    ```
    *(Returns `[]` if no customers.)*

---

### Inventory API

#### 1. Create Package Request
*   `POST /package_requests`
    *(Typically called by CRM integration)*
*   **Request Body (JSON):**
    ```json
    {
        "customer_id": 1,
        "package_type": "welcome_pack_v1"
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": 1,
        "customer_id": 1,
        "package_type": "welcome_pack_v1",
        "status": "received"
    }
    ```

#### 2. List Package Requests
*   `GET /package_requests`
*   **Success Response (200 OK):** A list of package requests. *(Note: Swagger UI docs for this endpoint might be minimal).*

## Integration Flow
1.  Client `POST`s new customer data to `/customers` (CRM API).
2.  CRM API saves the customer to its in-memory store.
3.  CRM API then internally calls `POST /package_requests` (Inventory API), sending the new customer's ID.
    *   If this internal call fails, it retries up to 3 times with a short delay.
4.  Inventory API receives the call and creates a package request in its in-memory store.
5.  CRM API responds to the original client with customer details and the status of the package request attempt.
    *   Customer creation in CRM succeeds even if the package request to Inventory ultimately fails after retries (an error is logged).

