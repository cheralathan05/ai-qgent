import socket
import time
import subprocess
import os
import sys
import urllib.request
import urllib.error
import json

print("Checking if APA-OS Backend is running...")

# Try to connect to port 8000
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("✓ Server is running on localhost:8000")
    else:
        print("✗ Server is not running on localhost:8000")
        sys.exit(1)
        
except Exception as e:
    print(f"Error checking server: {e}")
    sys.exit(1)

print("\n✓ Server is confirmed running!")

# Test the API endpoint
print("\nTesting /api/phase2/messages/send endpoint...")

url = 'http://localhost:8000/api/phase2/messages/send'
data = {
    "device_id": "7f0deaf6",
    "app": "whatsapp",
    "recipient": "8668180041",
    "message": "Good Morning"
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
req.add_header('Content-Type', 'application/json')

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        response_data = response.read().decode('utf-8')
        print(f"Response Status: {response.status}")
        print(f"Response Body: {response_data}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    try:
        response_data = e.read().decode('utf-8')
        print(f"Response: {response_data}")
    except:
        pass
except urllib.error.URLError as e:
    print(f"URL Error: {str(e)}")
except Exception as e:
    print(f"Unexpected Error: {str(e)}")

print("\nTest completed!")
