import asyncio
import sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def main():
    adb = get_adb_service(find_adb_binary())
    device_id = '7f0deaf6'
    print('=== Testing ADB commands ===')
    
    print('1. Waking device...')
    await adb.shell(device_id, 'input keyevent 26')
    await asyncio.sleep(1)
    
    print('2. Pressing HOME...')
    await adb.shell(device_id, 'input keyevent 3')
    await asyncio.sleep(2)
    
    print('3. Opening settings...')
    await adb.open_app(device_id, 'settings')
    await asyncio.sleep(3)
    
    print('4. Checking foreground...')
    fg = await adb.get_foreground_app(device_id)
    print(f'   Foreground: {fg}')
    
    print('=== DONE ===')

asyncio.run(main())
