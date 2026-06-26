import requests, json, sys

url = "http://127.0.0.1:8765/api/phase2/command"
headers = {"Content-Type": "application/json"}

tests = [
    "Open settings",
    "Turn on Wi-Fi",
    "What is the battery level",
    "Go to YouTube",
]

for cmd in tests:
    payload = {"command": cmd, "device_id": "7f0deaf6"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        data = resp.json()
        print(f"[{resp.status_code}] {cmd}")
        print(f"  success: {data.get('success')}")
        exec_result = data.get("execution", {})
        print(f"  action: {exec_result.get('action', exec_result.get('error', 'N/A'))}")
        print()
    except Exception as e:
        print(f"[ERROR] {cmd}: {e}")
        print()
