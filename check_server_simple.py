import socket
import time
import sys

print("Checking if APA-OS Backend is running...")

# Try to connect to port 8000
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("SUCCESS: Server is running on localhost:8000")
        sock.close()
    else:
        print("FAILURE: Server is not running on localhost:8000")
        print("Note: The server might be running but not bound to localhost:8000")
        sys.exit(1)
        
except Exception as e:
    print(f"Error checking server: {e}")
    sys.exit(1)

print("\nServer is confirmed running!")

print("\nNote: The API endpoint /api/phase2/messages/send should be available.")
print("The user requested to send a message:")
print("  Device: 7f0deaf6")
print("  App: whatsapp")
print("  Recipient: 8668180041")
print("  Message: Good Morning")

print("\nTo test the API with Python (install requests module first):")
print("pip install requests")
print("Then run:")
print("""
import requests
import json

url = 'http://localhost:8000/api/phase2/messages/send'
data = {
    'device_id': '7f0deaf6',
    'app': 'whatsapp',
    'recipient': '8668180041',
    'message': 'Good Morning'
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
""")
