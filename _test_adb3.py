import asyncio
import sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def main():
    adb = get_adb_service(find_adb_binary())
    device_id = '7f0deaf6'
    print('=== Simple ADB test ===')
    
    # Check screen is on
    print('1. Power state:')
    out = await adb.shell(device_id, 'dumpsys power')
    for line in out.splitlines():
        if 'Display Power' in line or 'mWakefulness' in line:
            print(f'   {line.strip()}')
    
    print('\n2. Waking & unlocking...')
    await adb.shell(device_id, 'input keyevent KEYCODE_WAKEUP')
    await asyncio.sleep(1)
    
    #   Swipe to unlock
    await adb.shell(device_id, 'input touchscreen swipe 300 1000 300 100')
    await asyncio.sleep(2)
    
    print('3. Opening WhatsApp directly...')
    result = await adb.shell(device_id, 'monkey -p com.whatsapp 1')
    print(f'   Result: {result[:200]}')
    await asyncio.sleep(4)
    
    print('4. Foreground activity:')
    out = await adb.shell(device_id, 'dumpsys activity activities')
    for line in out.splitlines():
        if 'mResumedActivity' in line:
            print(f'   {line.strip()}')
    
    print('\n=== DONE ===')

asyncio.run(main())
