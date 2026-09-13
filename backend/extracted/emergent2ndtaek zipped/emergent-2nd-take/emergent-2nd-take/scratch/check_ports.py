import requests

for port in [8000, 8001, 8002, 8003, 8004, 8005]:
    try:
        resp = requests.get(f"http://localhost:{port}/api/auth/me", timeout=2)
        print(f"Port {port}: Status {resp.status_code}, Body: {resp.text[:100]}")
    except Exception as e:
        print(f"Port {port}: Error {e}")
