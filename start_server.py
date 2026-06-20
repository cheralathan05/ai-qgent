"""Start APA-OS server for testing."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from main import app
import uvicorn

uvicorn.run(app, host='127.0.0.1', port=8765, log_level='warning')
