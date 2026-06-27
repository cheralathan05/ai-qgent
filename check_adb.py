import sys; sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary
import asyncio, json

async def check():
    adb = get_adb_service(find_adb_binary())
    print(f'ADB path: {adb.adb_path}')
    try:
        devices = await adb.list_devices()
        print(f'Devices found: {devices}')
        if devices:
            for d in devices:
                sid = d['serial']
                status = await adb.get_device_status(sid)
                print(f'Device status for {sid}:')
                print(json.dumps(status, indent=2, default=str))
        else:
            print('NO DEVICES CONNECTED - phone has no reaction because ADB cannot see it')
            print('Check: USB debugging enabled? USB cable connected? Authorized on phone?')
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(check())
