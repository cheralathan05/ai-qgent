import asyncio, sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def check():
    adb = get_adb_service(find_adb_binary())
    d = '7f0deaf6'
    out = await adb.shell(d, 'dumpsys power')
    for line in out.splitlines():
        if 'Display Power' in line or 'mWakefulness' in line:
            print(line.strip())

asyncio.run(check())
