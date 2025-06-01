# Mini Integration Platform (Full)

This project connects a mock CRM and Inventory system. When a new customer is created, a welcome package request is sent to Inventory.

## Features
- Add and view customers (CRM)
- Create and list package requests (Inventory)
- Simple retry logic if Inventory fails
- Swagger UI documentation for all endpoints
- Dockerized services for easy setup
- Unit tests and concurrency test included
- Architecture diagram

## Architecture Diagram

```mermaid
graph TD
    A[Client] --> B[CRM Service (Port 5000)]
    B --> C{Retry Logic}
    C -->|Success| D[Inventory Service (Port 5001)]
    C -->|Fail| E[Log Error]
    D --> F[Package Store]
    B --> G[Customer Store]
```

## How to Run

### 1. Docker Compose
1. Ensure Docker is installed.
2. From project root, run:
   ```
   docker-compose up --build
   ```
3. Access:
   - CRM Swagger: http://localhost:5000/docs
   - Inventory Swagger: http://localhost:5001/docs

### 2. Manual (no Docker)
1. Create a Python virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate       # Mac/Linux
   venv\Scripts\activate        # Windows
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run Inventory service:
   ```
   python inventory_service.py
   ```
4. In another terminal, run CRM service:
   ```
   python crm_service.py
   ```
5. Use Swagger or curl:
   - http://localhost:5000/docs
   - http://localhost:5001/docs

## Testing

### Unit Tests
- **test_crm.py**: Tests for CRM logic (mocks Inventory)
- **test_inventory.py**: Tests for Inventory endpoints
- **test_concurrency.py**: Concurrency testing script

Run all tests with:
```
pytest
```

### Concurrency Test
```
python test_concurrency.py
```

## Files
- `crm_service.py`
- `inventory_service.py`
- `Dockerfile.crm`, `Dockerfile.inventory`
- `docker-compose.yml`
- `README.md`
- `requirements.txt`
- `test_crm.py`, `test_inventory.py`, `test_concurrency.py`
- `.gitignore`
- `architecture_diagram.md`
