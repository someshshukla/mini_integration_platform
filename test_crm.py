import unittest
import requests
import requests_mock
from crm_service import app, customers, lock

class CRMTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.testing = True
        # Clear any existing customers
        with lock:
            customers.clear()
            import crm_service
            crm_service.next_id = 1

    def test_create_customer_integration_success(self):
        with requests_mock.Mocker() as m:
            m.post("http://inventory:5001/package_requests", status_code=201, json={
                "id": 1,
                "customer_id": 1,
                "package_type": "welcome",
                "status": "received"
            })
            response = self.client.post('/customers', json={"name": "Joe", "email": "joe@example.com"})
            self.assertEqual(response.status_code, 201)
            data = response.get_json()
            self.assertEqual(data["integration_status"], "success")
            self.assertEqual(data["name"], "Joe")

    def test_create_customer_integration_fail(self):
        with requests_mock.Mocker() as m:
            m.post("http://inventory:5001/package_requests", exc=requests.exceptions.ConnectionError)
            response = self.client.post('/customers', json={"name": "Jane", "email": "jane@example.com"})
            self.assertEqual(response.status_code, 201)
            data = response.get_json()
            self.assertEqual(data["integration_status"], "failed")

    def test_missing_fields(self):
        response = self.client.post('/customers', json={"name": "NoEmail"})
        self.assertEqual(response.status_code, 400)

    def test_list_customers(self):
        with requests_mock.Mocker() as m:
            m.post("http://inventory:5001/package_requests", status_code=201)
            self.client.post('/customers', json={"name": "Test", "email": "test@example.com"})
        response = self.client.get('/customers')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)

if __name__ == '__main__':
    unittest.main()