"""
APA-OS Backend Main Application
Entry point for the production system
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure src is on the import path when running from project root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from devices import device_manager, WindowsDevice, AndroidDevice

# Import core modules
from config import Config
from database.connection import init_database, close_database
from services.adb_service import get_adb_service
from services.device_agent import get_device_agent
from services.redis_service import get_redis_service
from api.main import app as api_app, bootstrap_phase1_environment

# Initialize configuration
config = Config()

# Configure logging
LOG_FILE_PATH = os.path.join(ROOT_DIR, config.LOG_FILE)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
    ]
)

logger = logging.getLogger(__name__)
from console.event_stream import (
    get_event_manager,
    ConsoleEventSubscriber,
    DatabaseEventSubscriber,
    WebSocketEventSubscriber,
)
from plugin_framework.builtin_plugins import register_builtin_plugins

ws_event_subscriber = WebSocketEventSubscriber()


# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    logger.info("=" * 50)
    logger.info("APA-OS Backend Starting")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info(f"Debug: {config.DEBUG}")
    logger.info("=" * 50)
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise
    
    # Initialize event system
    event_manager = get_event_manager()
    event_manager.subscribe(ConsoleEventSubscriber())
    event_manager.subscribe(ws_event_subscriber)
    logger.info("Event stream initialized")

    # Persist events to database
    event_manager.subscribe(DatabaseEventSubscriber())
    logger.info("Event database subscriber initialized")

    # Initialize Redis
    try:
        redis_service = get_redis_service()
        await redis_service.connect()
        logger.info("Redis initialized")
    except Exception as exc:
        logger.warning(f"Redis initialization failed: {exc}")

    # Register local Windows laptop device
    device_manager.register_device(
        WindowsDevice(
            device_id="laptop",
            windows_user=os.getenv("USERNAME", "local"),
        )
    )
    logger.info("Local Windows device registered")

    # Register connected Android devices if ADB available
    try:
        await bootstrap_phase1_environment()
        logger.info("Connected Android devices registered")
    except Exception as exc:
        logger.warning(f"Android device registration failed: {exc}")

    # Register built-in plugins
    try:
        register_builtin_plugins()
        logger.info("Built-in plugins registered")
    except Exception as e:
        logger.warning(f"Plugin registration skipped: {e}")

    logger.info("All services initialized")
    
    yield
    
    # Shutdown
    logger.info("=" * 50)
    logger.info("APA-OS Backend Shutting Down")
    logger.info("=" * 50)

    try:
        close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Create FastAPI application
app = FastAPI(
    title="APA-OS Backend",
    description="Advanced Personalized AI Assistant Operating System",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers directly from your consolidated api/main app surface
for route in api_app.routes:
    app.routes.append(route)


# WebSocket endpoint for real-time events
@app.websocket("/ws/events/{client_id}")
async def websocket_events(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time event streaming

    Usage:
        ws = new WebSocket("ws://localhost:8000/ws/events/client-1");
        ws.onmessage = (event) => {
            console.log(JSON.parse(event.data));
        };
    """
    await websocket.accept()
    queue = ws_event_subscriber.add_client(client_id)

    try:
        logger.info(f"WebSocket client connected: {client_id}")

        while True:
            message = await queue.get()
            await websocket.send_text(message)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        ws_event_subscriber.remove_client(client_id)
        logger.info(f"WebSocket client disconnected: {client_id}")


# ==================== Phase 2 WebSocket Channels ====================

@app.websocket("/ws/screen/{client_id}")
async def websocket_screen(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "capture":
                from vision.screen_capture import get_screen_capture_service
                from services.adb_service import get_adb_service, find_adb_binary
                adb = get_adb_service(find_adb_binary())
                devices = await adb.list_devices()
                if devices:
                    result = await get_screen_capture_service().capture_from_adb(devices[0]["serial"])
                    if result.success:
                        await websocket.send_json({
                            "event": "screen_captured", "device_id": devices[0]["serial"],
                            "width": result.width, "height": result.height,
                            "filepath": result.filepath,
                        })
                    else:
                        await websocket.send_json({"event": "error", "message": result.error})
                else:
                    await websocket.send_json({"event": "error", "message": "No Android device"})
            else:
                await websocket.send_json({"event": "ack", "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"Screen WS client disconnected: {client_id}")


@app.websocket("/ws/navigation/{client_id}")
async def websocket_navigation(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"event": "navigation_ack", "client_id": client_id, "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"Navigation WS client disconnected: {client_id}")


@app.websocket("/ws/ocr/{client_id}")
async def websocket_ocr(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ocr":
                from vision.screen_capture import get_screen_capture_service
                from vision.ocr_service import get_ocr_service
                from services.adb_service import get_adb_service, find_adb_binary
                adb = get_adb_service(find_adb_binary())
                devices = await adb.list_devices()
                if devices:
                    capture = await get_screen_capture_service().capture_from_adb(devices[0]["serial"])
                    if capture.success and capture.image is not None:
                        ocr = await get_ocr_service().extract_text(capture.image)
                        await websocket.send_json({
                            "event": "ocr_completed", "device_id": devices[0]["serial"],
                            "full_text": ocr.full_text,
                            "texts": [{"text": t.text, "confidence": t.confidence, "x": t.x, "y": t.y}
                                      for t in ocr.texts[:30]],
                        })
                    else:
                        await websocket.send_json({"event": "error", "message": "Capture failed"})
                else:
                    await websocket.send_json({"event": "error", "message": "No Android device"})
            else:
                await websocket.send_json({"event": "ack", "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"OCR WS client disconnected: {client_id}")


@app.websocket("/ws/vision/{client_id}")
async def websocket_vision(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "analyze":
                from vision.screen_capture import get_screen_capture_service
                from vision.ocr_service import get_ocr_service
                from vision.ui_detector import get_ui_detector
                from vision.screen_classifier import get_screen_classifier
                from services.adb_service import get_adb_service, find_adb_binary
                adb = get_adb_service(find_adb_binary())
                devices = await adb.list_devices()
                if devices:
                    capture = await get_screen_capture_service().capture_from_adb(devices[0]["serial"])
                    if capture.success and capture.image is not None:
                        ocr = await get_ocr_service().extract_text(capture.image)
                        ui = await get_ui_detector().detect_elements(capture.image)
                        classification = await get_screen_classifier().classify(
                            image=capture.image, foreground_app=None,
                            text_content=ocr.full_text, ui_result=ui,
                        )
                        await websocket.send_json({
                            "event": "vision_analysis", "device_id": devices[0]["serial"],
                            "classification": classification.to_dict(),
                            "elements": {"buttons": len(ui.buttons), "inputs": len(ui.inputs),
                                         "total": len(ui.elements)},
                            "text_preview": ocr.full_text[:300],
                        })
                    else:
                        await websocket.send_json({"event": "error", "message": "Capture failed"})
                else:
                    await websocket.send_json({"event": "error", "message": "No Android device"})
            else:
                await websocket.send_json({"event": "ack", "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"Vision WS client disconnected: {client_id}")


@app.websocket("/ws/messages/{client_id}")
async def websocket_messages(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"event": "messages_ack", "client_id": client_id, "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"Messages WS client disconnected: {client_id}")


@app.websocket("/ws/memory/{client_id}")
async def websocket_memory(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "status":
                from vision.phone_memory import get_phone_memory
                memory = get_phone_memory()
                devs = list(memory._screens.keys()) if hasattr(memory, '_screens') else []
                await websocket.send_json({
                    "event": "memory_status", "devices_with_memory": devs,
                })
            else:
                await websocket.send_json({"event": "ack", "received": data})
    except Exception:
        pass
    finally:
        logger.info(f"Memory WS client disconnected: {client_id}")


# Register Phase 2 API router
from api.phase2 import router as phase2_router
app.include_router(phase2_router, prefix="/api/phase2")


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "APA-OS Backend",
        "version": "1.0.0",
        "status": "running",
    }


def run_server():
    """Run the API server"""
    logger.info(f"Starting server on {config.API_HOST}:{config.API_PORT}")
    
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        workers=config.API_WORKERS if not config.DEBUG else 1,
        reload=config.DEBUG,
        reload_excludes=[config.LOG_FILE],
        log_level=config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    try:
        # Disable uvicorn auto-reload when invoked directly to avoid filesystem loops on Windows
        start_port = config.API_PORT
        max_tries = 5
        import socket

        for attempt in range(max_tries):
            port = start_port + attempt

            # Quick check: attempt to bind a temporary socket to ensure port availability
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind((config.API_HOST, port))
                sock.close()
            except OSError:
                logger.warning(f"Port {port} unavailable, trying next port")
                if attempt == max_tries - 1:
                    logger.error("Failed to bind to any port; exiting")
                    raise
                continue

            # Port is free; start server on this port
            uvicorn.run(
                "main:app",
                host=config.API_HOST,
                port=port,
                workers=config.API_WORKERS if not config.DEBUG else 1,
                reload=False,
                reload_excludes=[config.LOG_FILE],
                log_level=config.LOG_LEVEL.lower(),
            )
            break
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)