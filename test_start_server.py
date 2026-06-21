import sys, os
sys.path.insert(0, r'C:\Users\chera\Downloads\ai-agent\src')
os.chdir(r'C:\Users\chera\Downloads\ai-agent')
from main import app
import uvicorn
uvicorn.run(app, host='127.0.0.1', port=9878, log_level='error')
