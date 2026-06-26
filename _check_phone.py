import asyncio, sys
sys.path.insert(0, 'src')
from services.adb_service import get_adb_service, find_adb_binary

async def check():
    adb = get_adb_service(find_adb_binary())
    d = '7f0deaf6'
    
    print('=== PHONE STATE ===')
    
    # Full dumpsys for activities
    out = await adb.shell(d, 'dumpsys activity activities')
    for line in out.splitlines():
        if 'ResumedActivity' in line:
            print(f'  Resumed: {line.strip()}')
    
    # Try Task info
    out = await adb.shell(d, 'dumpsys activity recents')
    for line in out.splitlines():
        if 'Recent #0' in line:
            print(f'  Recent: {line.strip()[:200]}')
    
    # Try wm
    out = await adb.shell(d, 'dumpsys window windows')
    for line in out.splitlines():
        if 'mCurrentFocus' in line:
            print(f'  Focus: {line.strip()[:200]}')
        elif 'mFocusedApp' in line:
            print(f'  FocusedApp: {line.strip()[:200]}')
    
    # Current input method
    out = await adb.shell(d, 'dumpsys input_method')
    for line in out.splitlines():
        if 'mCurFocusedWindow' in line:
            print(f'  Input: {line.strip()[:200]}')
    
    print('\nTesting actual commands on phone...')
    
    # Press home
    print('1. Press HOME')
    await adb.shell(d, 'input keyevent KEYCODE_HOME')
    await asyncio.sleep(2)
    
    out = await adb.shell(d, 'dumpsys window windows')
    for line in out.splitlines():
        if 'mCurrentFocus' in line:
            print(f'   After HOME - Focus: {line.strip()[:200]}')
    
    # Open settings by package
    print('2. Open Settings')
    await adb.shell(d, 'am start -a android.settings.SETTINGS')
    await asyncio.sleep(3)
    
    out = await adb.shell(d, 'dumpsys window windows')
    for line in out.splitlines():
        if 'mCurrentFocus' in line:
            print(f'   After SETTINGS - Focus: {line.strip()[:200]}')
    
    print('\n=== DONE ===')

asyncio.run(check())
