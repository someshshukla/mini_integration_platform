import unittest
import json
import requests_mock


import app as app_module 



class MiniPlatformIntegrationTests(unittest.TestCase): 
    """
    Tests for our little CRM-Inventory integration.
    Trying to cover the main paths and some error cases.
    """

    original_retry_delay_val = None 

    @classmethod
    def setUpClass(cls):
        """
        Set up things once for the whole test class.
        Mainly for storing and overriding the retry delay globally for all tests.
        """
        cls.original_retry_delay_val = app_module.INTEGRATION_RETRY_WAIT_SECONDS
        app_module.INTEGRATION_RETRY_WAIT_SECONDS = 0.01 

    @classmethod
    def tearDownClass(cls):
        """
        Restore things after all tests in the class are done.
        """
        app_module.INTEGRATION_RETRY_WAIT_SECONDS = cls.original_retry_delay_val
      

    def setUp(self):
        """
        This runs before each test method.
        Good for resetting state, like our in-memory "databases".
        """
        self.flask_app = app_module.app 
        self.app_context = self.flask_app.app_context()
        self.app_context.push()
        self.test_client = self.flask_app.test_client() 
        self.flask_app.testing = True

        app_module.customers_db.clear() 
        app_module.package_requests_db.clear()
        app_module.next_customer_id_counter = 1
        app_module.next_package_request_id_counter = 1
    

    def tearDown(self):
        """
        This runs after each test method.
        Good for any cleanup, like popping the app context.
        """
        self.app_context.pop()
        

    def test_scenario_add_customer_and_inventory_call_works_first_time(self):
        """
        Happy path: New customer, inventory call for package works immediately.
        """
       
        with requests_mock.Mocker() as m:
        
            m.post(app_module.INVENTORY_SERVICE_URL, 
                   json={"id": 1, "customer_id": 1, "package_type": "welcome", "status": "received"}, 
                   status_code=201)

            customer_data = {"name": "Happy Path User", "email": "happy@example.com"}
            response = self.test_client.post('/customers', 
                                             data=json.dumps(customer_data), 
                                             content_type='application/json')
            
            self.assertEqual(response.status_code, 201, "Adding customer should be successful (201)")
            
            response_json = json.loads(response.data)
            self.assertEqual(response_json['name'], "Happy Path User")
            self.assertEqual(response_json['id'], 1, "First customer should get ID 1")
            
            self.assertIn("Package request created successfully", response_json['integration_status'])
            self.assertIn("on attempt 1", response_json['integration_status'])


            self.assertIn(1, app_module.customers_db, "Customer ID 1 should be in customers_db")
        
        
            self.assertEqual(m.call_count, 1, "Inventory service should have been called exactly once")


    def test_scenario_add_customer_and_inventory_works_on_a_retry(self):
        """
        Test when the inventory call fails once, then succeeds on the second try.
        """
        with requests_mock.Mocker() as m:
            
            m.post(app_module.INVENTORY_SERVICE_URL, [
                {'status_code': 503, 'text': 'Inventory Service Temporarily Down'}, 
                {'status_code': 201, 'json': {"id": 1, "customer_id": 1, "package_type": "welcome", "status": "received"}}
            ])

            customer_data = {"name": "Retry Success User", "email": "retry@example.com"}
            response = self.test_client.post('/customers', data=json.dumps(customer_data), content_type='application/json')

            self.assertEqual(response.status_code, 201)
            response_json = json.loads(response.data)
            self.assertEqual(response_json['id'], 1)
            self.assertIn("Package request created successfully", response_json['integration_status'])
            self.assertIn("on attempt 2", response_json['integration_status'], "Should succeed on the 2nd attempt")

            self.assertIn(1, app_module.customers_db)
            self.assertEqual(m.call_count, 2, "Inventory service should be called twice (1 fail, 1 success)")


    def test_scenario_add_customer_but_inventory_fails_all_retries(self):
        """
        Customer is added, but all attempts to call inventory fail.
        The CRM operation itself should still succeed.
        """
        with requests_mock.Mocker() as m:
            
            m.post(app_module.INVENTORY_SERVICE_URL, status_code=500, text='Permanent Inventory Error')

            customer_data = {"name": "Integration Fail User", "email": "integfail@example.com"}
            response = self.test_client.post('/customers', data=json.dumps(customer_data), content_type='application/json')

            self.assertEqual(response.status_code, 201, "Customer creation should still be 201 even if integration fails")
            response_json = json.loads(response.data)
            self.assertEqual(response_json['id'], 1)
            
            self.assertIn(f"Failed to create package request for customer 1 after {app_module.MAX_INTEGRATION_ATTEMPTS} attempts", response_json['integration_status'])

            self.assertIn(1, app_module.customers_db)
        
            self.assertTrue(not app_module.package_requests_db, "Package requests DB should be empty") 
            self.assertEqual(m.call_count, app_module.MAX_INTEGRATION_ATTEMPTS, "Should have tried max attempts")

    
    def test_error_add_customer_with_missing_email(self):
        """
        Try to add a customer but forget the email field. Should get a 400.
        """
        customer_data_bad = {"name": "Forgetful User"} 
        response = self.test_client.post('/customers', data=json.dumps(customer_data_bad), content_type='application/json')
        
        self.assertEqual(response.status_code, 400, "Expected a 400 Bad Request for missing fields")
        response_json = json.loads(response.data)
        self.assertIn("Missing required fields", response_json.get('error', '')) 
        self.assertIn("email", response_json.get('error', ''))

    
    def test_list_customers_when_db_is_empty(self):
        """
        Call GET /customers when no customers have been added. Should be an empty list.
        """
        response = self.test_client.get('/customers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), [], "Expected an empty list for no customers")

    def test_list_customers_after_adding_one(self):
        """
        Add a customer, then list customers. Should see the one we added.
        """
        
        with requests_mock.Mocker() as m:
            m.post(app_module.INVENTORY_SERVICE_URL, status_code=201) 
            customer_to_add = {"name": "Lister User", "email": "lister@example.com"}
            add_resp = self.test_client.post('/customers', data=json.dumps(customer_to_add), content_type='application/json')
            self.assertEqual(add_resp.status_code, 201) 

        list_response = self.test_client.get('/customers')
        self.assertEqual(list_response.status_code, 200)
        
        customers_list_json = json.loads(list_response.data)
        self.assertEqual(len(customers_list_json), 1, "Should be one customer in the list")
        
        
        retrieved_customer = customers_list_json[0]
        self.assertEqual(retrieved_customer['name'], "Lister User")
        self.assertEqual(retrieved_customer['email'], "lister@example.com")
        self.assertEqual(retrieved_customer['id'], 1) 

    def test_inventory_api_create_package_request_directly(self):
        """
        Test calling the POST /package_requests endpoint of the Inventory API directly.
        This ensures the inventory part itself works. No mocking of requests here.
        """
        package_data = {"customer_id": 777, "package_type": "special_promo_pack"}
        response = self.test_client.post('/package_requests', 
                                         data=json.dumps(package_data), 
                                         content_type='application/json')
        
        self.assertEqual(response.status_code, 201, "Direct package request creation should be 201")
        
        response_json = json.loads(response.data)
        self.assertEqual(response_json['customer_id'], 777)
        self.assertEqual(response_json['package_type'], "special_promo_pack")
        self.assertEqual(response_json['status'], "received") 
        self.assertIn('id', response_json)

        
        self.assertIn(response_json['id'], app_module.package_requests_db) 
        stored_package = app_module.package_requests_db[response_json['id']]
        self.assertEqual(stored_package['customer_id'], 777)

    def test_inventory_api_create_package_request_missing_data(self):
        """Inventory: Try to create a package request but miss a field."""
        bad_package_data = {"customer_id": 888} 
        response = self.test_client.post('/package_requests', 
                                         data=json.dumps(bad_package_data), 
                                         content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertIn("customer_id and package_type are required", response_json.get('error', ''))


if __name__ == '__main__':

    unittest.main(buffer=True)