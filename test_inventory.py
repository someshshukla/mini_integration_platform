# Unit tests for Inventory service

import unittest
from inventory_service import app, packages, lock

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.testing = True
        with lock:
            packages.clear()
            import inventory_service
            inventory_service.next_pid = 1

    def test_create_package_success(self):
        response = self.client.post('/package_requests', json={"customer_id": 5, "package_type": "welcome"})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["customer_id"], 5)
        self.assertEqual(data["package_type"], "welcome")
        self.assertEqual(data["status"], "received")

    def test_create_package_missing(self):
        response = self.client.post('/package_requests', json={"customer_id": 5})
        self.assertEqual(response.status_code, 400)

    def test_list_packages(self):
        self.client.post('/package_requests', json={"customer_id": 1, "package_type": "welcome"})
        response = self.client.get('/package_requests')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 1)

if __name__ == '__main__':
    unittest.main()
