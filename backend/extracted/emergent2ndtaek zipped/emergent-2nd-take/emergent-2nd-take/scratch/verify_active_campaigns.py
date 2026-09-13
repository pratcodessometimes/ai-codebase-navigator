import requests

url = "http://localhost:8000/api/campaigns"
try:
    resp = requests.get(url, params={"status": "ACTIVE"})
    print(f"Status code: {resp.status_code}")
    print(f"Response body (truncated): {resp.text[:500]}")
    data = resp.json()
    print(f"\nNumber of active campaigns returned: {len(data)}")
    for i, c in enumerate(data):
        print(f"  {i+1}. Title: {c.get('title')}, Status: {c.get('status')}, ID: {c.get('campaign_id')}")
except Exception as e:
    print(f"Error querying active campaigns: {e}")
