import asyncio
import sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def main():
    adb = get_adb_service(find_adb_binary())
    device_id = '7f0deaf6'
    print('=== Detailed ADB test ===')
    
    # Check device state
    devices = await adb.list_devices()
    print(f'Devices: {devices}')
    
    # Try direct shell commands
    print('\n1. Direct shell: wm size')
    out = await adb.shell(device_id, 'wm size')
    print(f'   Output: {out.strip()}')
    
    print('\n2. Direct shell: dumpsys window displays')
    out = await adb.shell(device_id, 'dumpsys window displays')
    print(f'   Output: {out[:300].strip()}')
    
    # Check if screen is on
    print('\n3. Checking power state')
    out = await adb.shell(device_id, 'dumpsys power 2>&1 | findstr "Display Power"')
    print(f'   raw: {out[:200].strip()}')
    
    # Try to wake the phone properly
    print('\n4. Waking up...')
    await adb.shell(device_id, 'input keyevent KEYCODE_WAKEUP')
    await asyncio.sleep(2)
    
    # Unlock with swipe
    print('\n5. Swiping to unlock...')
    await adb.shell(device_id, 'input touchscreen swipe 300 1000 300 300')
    await asyncio.sleep(2)
    
    # Press home
    print('\n6. Pressing home...')
    await adb.shell(device_id, 'input keyevent KEYCODE_HOME')
    await asyncio.sleep(2)
    
    # Check foreground
    print('\n7. Foreground app (raw dumpsys):')
    out = await adb.shell(device_id, 'dumpsys activity activities 2>&1 | findstr "mResumedActivity"')
    print(f'   Output: {out[:300].strip()}')
    
    # Try to open apps package directly
    print('\n8. Opening settings via package...')
    await adb.shell(device_id, 'am start -a android.settings.SETTINGS')
    await asyncio.sleep(3)
    
    out = await adb.shell(device_id, 'dumpsys activity activities 2>&1 | findstr "mResumedActivity"')
    print(f'   Foreground: {out[:300].strip()}')
    
    print('\n=== DONE ===')

asyncio.run(main())
