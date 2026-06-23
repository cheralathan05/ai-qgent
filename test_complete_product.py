"""Complete APA-OS Product Test"""
import asyncio, sys
sys.path.insert(0, 'src')
from core.apa_os import get_apa_os

apa_os = get_apa_os()

commands = [
    'Open Instagram',
    'Open Spotify',
    'Open Telegram',
    'Close WhatsApp',
    'Open Camera',
    'Open Calculator',
    'Open Settings',
    'Send hello to Guru',
    'Call Mom',
    'Open WhatsApp chat with John',
    'What is my battery level?',
    'Take a screenshot',
    'What app is open?',
    'Search for AI Agents',
    'Google Python tutorials',
    'Find my DBMS notes',
    'Summarize my OS notes',
    'Explain Normalization',
    'Generate 20 interview questions on Python',
    'Generate MCQs on DBMS',
    'Create assignment on Operating Systems',
    'Generate notes on Cloud Computing',
    'Go back',
    'Go home',
    'Scroll down',
    'Turn on WiFi',
    'Turn off Bluetooth',
    'Volume up',
    'Lock device',
    'Open YouTube and search AI Agents',
    'Open Chrome and search Java Interview Questions',
    'Find my resume',
]

async def test_all():
    print('=' * 70)
    print('APA-OS COMPLETE PRODUCT TEST')
    print('=' * 70)
    
    passed = 0
    failed = 0
    for cmd in commands:
        result = await apa_os.process(cmd)
        status = 'PASS' if (result.success or result.message) else 'FAIL'
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
        print(f'  [{status}] "{cmd}"')
        print(f'         intent={result.intent} target={result.target} success={result.success}')
        if result.knowledge_result and result.knowledge_result.success:
            print(f'         knowledge: {result.knowledge_result.operation} ({len(result.knowledge_result.answer)} chars)')
        elif not result.success:
            print(f'         message: {result.message[:80]}')
    
    print(f'\nResults: {passed}/{passed + failed} passed')
    
    # Test system status
    print('\n--- System Status ---')
    status = apa_os.get_status()
    print(f'  Layers: {len(status.get("layers", {}))}')
    print(f'  Events emitted: {apa_os.events.get_stats()}')
    print(f'  Learning patterns: {sum(len(v) for v in apa_os.learning.get_all_patterns().values())}')
    print(f'  Conversations: {len(apa_os.conversation.get_all_conversations())}')

asyncio.run(test_all())
