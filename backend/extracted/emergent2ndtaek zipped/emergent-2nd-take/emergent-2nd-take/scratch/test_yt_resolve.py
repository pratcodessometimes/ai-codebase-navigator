import os
import requests
from dotenv import load_dotenv

# Load env file from backend/.env
load_dotenv("backend/.env")

api_key = os.getenv("YOUTUBE_API_KEY")
print(f"API Key: {api_key}")

def resolve_channel(handle_or_id: str):
    print(f"\nResolving: {handle_or_id}")
    params = {
        "part": "snippet",
        "key": api_key
    }
    if handle_or_id.startswith("UC") and len(handle_or_id) == 24:
        params["id"] = handle_or_id
    else:
        # Ensure it has @ prefix
        handle = handle_or_id if handle_or_id.startswith("@") else f"@{handle_or_id}"
        params["forHandle"] = handle
    
    resp = requests.get("https://www.googleapis.com/youtube/v3/channels", params=params)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        if items:
            item = items[0]
            print(f"Channel ID: {item.get('id')}")
            snippet = item.get("snippet", {})
            print(f"Title: {snippet.get('title')}")
            print(f"Custom URL (Handle): {snippet.get('customUrl')}")
            print(f"Description: {repr(snippet.get('description'))}")
        else:
            print("No items found.")
    else:
        print(resp.text)

# Test both handles from the user request
resolve_channel("@skills-vo1zp")
resolve_channel("@broisoutclipped")
