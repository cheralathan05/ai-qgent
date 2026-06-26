#!/usr/bin/env python3
import os
os.chdir(r'C:\Users\chera\Downloads\ai-agent')

import subprocess
import time
import urllib.request
import urllib.error
import json
import sys

print("Starting APA-OS Backend server for testing...")

# Set environment
env = os.environ.copy()
env['PYTHONPATH'] = os.path.join(os.getcwd(), 'src') + ':' + env.get('PYTHONPATH', '')

# Start the server
proc = subprocess.Popen([sys.executable, 'main.py'], 
                       env=env, 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(5)

# Test the messages/send endpoint
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
    with urllib.request.urlopen(req, timeout=10) as response:
        response_data = response.read().decode('utf-8')
        print(f"Response Status: {response.status}")
        print(f"Response Body: {response_data}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    try:
        print(f"Response: {e.read().decode('utf-8')}")
    except:
        pass
except urllib.error.URLError as e:
    print(f"URL Error: {str(e)}")
except Exception as e:
    print(f"Unexpected Error: {str(e)}")

# Kill the server
print("\nShutting down server...")
proc.terminate()
proc.wait(timeout=5)
print("Test completed.")
