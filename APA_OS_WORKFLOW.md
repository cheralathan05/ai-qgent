# APA-OS Unified Workflow Engine

## Architecture Overview

APA-OS is a Personal AI Operating System with three integrated layers:

```
Phase 1: Device Control Layer     - Control the phone
Phase 2: Phone Intelligence Layer - Understand the phone
Phase 3: Knowledge Layer          - Understand user knowledge
```

All three layers operate as one unified platform through the **Unified Workflow Engine**.

---

## Complete Workflow Pipeline

```
Voice/Text Input
     ↓
┌─────────────────────────────────────────────────────────┐
│              UNIFIED WORKFLOW ENGINE                     │
├─────────────────────────────────────────────────────────┤
│ 1. Intent Detection     - What does the user want?      │
│ 2. Entity Extraction    - Extract app, contact, etc.    │
│ 3. App Resolution       - Find package name dynamically │
│ 4. ADB Launch           - Execute on Android device     │
│ 5. Verification         - Confirm action succeeded      │
│ 6. Response             - Return result to user         │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Base URL
```
http://localhost:8000/v1
```

### 1. Execute Command
```http
POST /v1/command
Content-Type: application/json

{
  "command": "Open Spotify",
  "device_id": "optional-device-serial",
  "user_id": "default",
  "voice_input": false
}
```

**Response:**
```json
{
  "success": true,
  "workflow_id": "wf_1234567890",
  "intent": "open_app",
  "target": "spotify",
  "message": "Spotify is ready.",
  "package_name": "com.spotify.music",
  "foreground_app": "com.spotify.music",
  "verification_passed": true,
  "duration_ms": 2450.5,
  "steps": [
    {"step": 1, "type": "intent_detection", "status": "completed"},
    {"step": 2, "type": "app_resolution", "status": "completed"},
    {"step": 3, "type": "execute_action", "status": "completed"},
    {"step": 4, "type": "verification", "status": "completed"}
  ]
}
```

### 2. Quick Open App
```http
GET /v1/open?app_name=spotify
```

### 3. Get Installed Apps
```http
GET /v1/device/apps
```

**Response:**
```json
{
  "total": 150,
  "apps": [
    {"package_name": "com.spotify.music", "app_label": "Spotify"},
    {"package_name": "org.telegram.messenger", "app_label": "Telegram"},
    {"package_name": "com.instagram.android", "app_label": "Instagram"},
    ...
  ]
}
```

### 4. Search Apps
```http
GET /v1/device/apps/search?q=spotify
```

### 5. Refresh App Registry
```http
POST /v1/device/apps/refresh
```

### 6. Device Status
```http
GET /v1/device/status
```

### 7. Battery Level
```http
GET /v1/device/battery
```

### 8. Foreground App
```http
GET /v1/device/foreground
```

### 9. Health Check
```http
GET /v1/health
```

---

## Supported Commands

### App Control
| Command | Intent | Example |
|---------|--------|---------|
| Open [app] | open_app | Open Spotify |
| Close [app] | close_app | Close Instagram |
| Open Camera | open_camera | Open Camera |
| Open Settings | open_settings | Open Settings |

### Messaging
| Command | Intent | Example |
|---------|--------|---------|
| Send [msg] to [person] | send_message | Send hello to Guru |
| Open [app] chat | open_chat | Open WhatsApp chat |
| Call [person] | call_contact | Call Mom |

### Device Info
| Command | Intent | Example |
|---------|--------|---------|
| Battery level | battery_status | What's my battery level? |
| Current app | foreground_app | What app is open? |
| Take screenshot | take_screenshot | Take a screenshot |

### Search
| Command | Intent | Example |
|---------|--------|---------|
| Search [query] | search | Search for AI Agents |
| Google [query] | web_search | Google Python tutorials |
| Search [query] on YouTube | search | Search AI on YouTube |

---

## Supported Apps

The system dynamically discovers all installed apps. Common apps include:

| App Name | Package Name |
|----------|--------------|
| Instagram | com.instagram.android |
| WhatsApp | com.whatsapp |
| Telegram | org.telegram.messenger |
| Chrome | com.android.chrome |
| YouTube | com.google.android.youtube |
| Spotify | com.spotify.music |
| Camera | com.android.camera |
| Calculator | com.android.calculator2 |
| Settings | com.android.settings |
| Gmail | com.google.android.gm |
| Maps | com.google.android.apps.maps |

---

## Workflow Phases

### Phase 1: Device Control
- Open/Close apps
- Take screenshots
- Check battery
- Get foreground app
- Input text/commands

### Phase 2: Phone Intelligence
- Screen classification
- Visual verification
- Navigation tracking
- OCR text extraction
- UI element detection

### Phase 3: Knowledge
- Document search
- File lookup
- Memory tracking
- Context awareness

---

## Verification System

Every action is verified before returning success:

```python
# For app launches
foreground_app = await adb.get_foreground_app(device_id)
verification_passed = foreground_app == expected_package

# For messages
message_verified = check_ocr_for_message_text()

# For screenshots
screenshot_taken = filepath is not None
```

---

## Error Handling

```json
{
  "success": false,
  "message": "App 'xyz' is not installed on your device",
  "error": "App not found"
}
```

---

## Quick Start

1. Start the server:
```bash
cd src
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

2. Test with curl:
```bash
# Open any app
curl -X POST http://localhost:8000/v1/command \
  -H "Content-Type: application/json" \
  -d '{"command": "Open Spotify"}'

# Get installed apps
curl http://localhost:8000/v1/device/apps

# Check device status
curl http://localhost:8000/v1/device/status
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INPUT                             │
│                   (Voice/Text)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  INTENT AGENT                                │
│   - Command normalization                                   │
│   - Intent classification                                  │
│   - Entity extraction                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                APP RESOLVER                                  │
│   - Dynamic package discovery                              │
│   - Fuzzy matching                                         │
│   - Alias resolution                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                ADB SERVICE                                   │
│   - Monkey launch                                          │
│   - Activity launch                                        │
│   - Deep links                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              VERIFICATION                                   │
│   - Foreground app check                                   │
│   - OCR verification                                       │
│   - Screen classification                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   RESPONSE                                  │
│   - Success/Failure                                        │
│   - Message                                                │
│   - Metadata                                               │
└─────────────────────────────────────────────────────────────┘
```
