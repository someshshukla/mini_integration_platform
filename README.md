 {
     "id": 1,
     "name": "Somesh Shukla",
     "email": "orionbee13@gmail.com",
     "integration_status": "Package request created successfully..." // Or failure message
 }
 ```
 Error Response (400 Bad Request):
 ```json
 { "error": "Missing required fields: email" }
 ```

#### 2. View Customers
 `GET /customers`
  Success Response (200 OK):
 ```json
 [
     { "id": 1, "name": "Somesh Shukla", "email": "orionbee13@gmail.com" }
 ]
 ```
 (Returns `[]` if no customers.)

---

### Inventory API

#### 1. Create Package Request
 `POST /package_requests`
 (Typically called by CRM integration)
 Request Body (JSON):
 ```json
 {
     "customer_id": 1,
     "package_type": "welcome_pack_v1"
 }
 ```
 Success Response (201 Created):
 ```json
 {
     "id": 1,
     "customer_id": 1,
     "package_type": "welcome_pack_v1",
     "status": "received"
 }
 ```

#### 2. List Package Requests
`GET /package_requests`
Success Response (200 OK): A list of package requests. 

## Integration Flow
1.  Client `POST`s new customer data to `/customers` (CRM API).
2.  CRM API saves the customer to its in-memory store.
3.  CRM API then internally calls `POST /package_requests` (Inventory API), sending the new customer's ID.
 If this internal call fails, it retries up to 3 times with a short delay.
4.  Inventory API receives the call and creates a package request in its in-memory store.
5.  CRM API responds to the original client with customer details and the status of the package request attempt.
 Customer creation in CRM succeeds even if the package request to Inventory ultimately fails after retries (an error is logged).

## Cloud
Docker: A `Dockerfile` is provided for containerization.
Testing: Unit tests (`test_app.py`) are included and can be run with `python -m unittest test_app.py`.