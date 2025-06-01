# Concurrency test: send multiple customer creation requests at once

import requests
import threading

def add_cust(i):
    payload = {"name": f"Concurrent User {i}", "email": f"concurrent{i}@example.com"}
    try:
        response = requests.post("http://localhost:5000/customers", json=payload)
        print(f"User {i}: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"User {i} Error: {e}")

threads = []
for i in range(5):
    t = threading.Thread(target=add_cust, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
