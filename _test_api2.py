"""Verify the API actually executes on phone."""
import requests, asyncio, sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def get_fg(adb, d):
    out = await adb.shell(d, 'dumpsys activity activities')
    for line in out.splitlines():
        if 'ResumedActivity' in line:
            return line.strip()
    return None

async def test():
    adb = get_adb_service(find_adb_binary())
    d = '7f0deaf6'
    
    print('=== BEFORE ===')
    before = await get_fg(adb, d)
    print(f'  {before}')
    
    print('\nSend "Open settings"...')
    resp = requests.post('http://127.0.0.1:8765/api/phase2/command', json={
        'command': 'Open settings',
        'device_id': d
    }, timeout=30)
    print(f'  API: {resp.json()["success"]} - {resp.json()["execution"]["action"]}')
    
    await asyncio.sleep(3)
    
    print('\n=== AFTER ===')
    after = await get_fg(adb, d)
    print(f'  {after}')
    
    if 'settings' in (after or '').lower():
        print('\nVERIFIED: Phone reacted - Settings opened!')
    else:
        print('\nPhone did NOT react to command')
    
    print('\nTry "Turn on Wi-Fi"...')
    resp2 = requests.post('http://127.0.0.1:8765/api/phase2/command', json={
        'command': 'Turn on Wi-Fi',
        'device_id': d
    }, timeout=30)
    print(f'  API: {resp2.json()["success"]} - {resp2.json()["execution"]["action"]}')
    
    print('\nTry "What is battery level"...')
    resp3 = requests.post('http://127.0.0.1:8765/api/phase2/command', json={
        'command': 'What is battery level',
        'device_id': d
    }, timeout=30)
    data = resp3.json()
    print(f'  API: {data["success"]} - battery: {data["execution"].get("battery_level", "?")}')

asyncio.run(test())
