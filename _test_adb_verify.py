"""Verify ADB execution from the API endpoint."""
import requests, json, asyncio, sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def check_phone():
    adb = get_adb_service(find_adb_binary())
    device_id = '7f0deaf6'
    
    print('=== PRE-EXECUTION STATE ===')
    fg = await adb.shell(device_id, 'dumpsys activity activities')
    for line in fg.splitlines():
        if 'mResumedActivity' in line:
            print(f'  Foreground: {line.strip()}')
    
    # Now call the API
    print('\n=== SENDING COMMAND ===')
    url = "http://127.0.0.1:8765/api/phase2/command"
    resp = requests.post(url, json={
        "command": "Open settings",
        "device_id": "7f0deaf6"
    }, timeout=30)
    print(f'  API response: {resp.json()}')
    
    await asyncio.sleep(3)
    
    print('\n=== POST-EXECUTION STATE ===')
    fg = await adb.shell(device_id, 'dumpsys activity activities')
    for line in fg.splitlines():
        if 'mResumedActivity' in line:
            print(f'  Foreground: {line.strip()}')
    
    # Check battery
    battery = await adb.shell(device_id, 'dumpsys battery')
    for line in battery.splitlines():
        if 'level' in line:
            print(f'  Battery: {line.strip()}')

asyncio.run(check_phone())
