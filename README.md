# APA-OS Backend - Production Grade

Advanced Personalized AI Assistant Operating System backend with comprehensive reliability, audit, and execution verification layers.

## Architecture Overview

The system is built with **8 production-grade layers**:

### 1. **Reliability Layer** (`src/reliability/`)
- `retry_manager.py` - Exponential backoff with configurable strategies
- `circuit_breaker.py` - Prevents cascading failures
- `timeout_manager.py` - Operation timeouts with grace handling
- `failure_classifier.py` - Automatic failure type detection and recovery suggestions
- Recovery workflows with escalation

### 2. **Audit Layer** (`src/audit/`)
- Complete audit trail of all operations
- Action logging with user tracking
- Workflow lifecycle tracking
- Security event logging

### 3. **Execution Verification** (`src/verification/`)
- Post-execution verification
- Screenshot-based validation
- State change confirmation
- Confidence scoring

### 4. **Device Intelligence** (`src/device_intelligence/`)
- Real-time device state detection
- App detection and permissions
- Battery/lock/screen state monitoring
- Capability detection

### 5. **Command Understanding** (`src/understanding/`)
- NLU entity extraction
- Intent classification
- Ambiguity resolution
- Command normalization

### 6. **Approval UI** (`src/approval_ui/`)
- Human approval workflows
- Payment verification
- Permission requests
- Confidence-based auto-approval

### 7. **Security** (`src/security/`)
- Credential encryption
- Vault integration
- PIN handling (temporary, never stored)
- Secret access logging

### 8. **Observability** (`src/observability/`)
- Distributed tracing
- Performance metrics
- Agent-level statistics
- Real-time event streaming

## Database Schema

The system uses PostgreSQL with comprehensive tracking:

```
workflows              - Main workflow executions
workflow_steps        - Individual steps within workflows
execution_steps       - Low-level execution details
agent_runs            - Agent call tracking
device_states         - Device state snapshots
approval_actions      - Approval history
audit_events          - Complete audit trail
event_snapshots       - Real-time console events
verification_results  - Execution verification
source_records        - Data provenance
system_metrics        - Performance metrics
agent_metrics         - Agent performance
workflow_metrics      - Workflow performance
failure_records       - Failure tracking with recovery info
```

## Real-Time Event Stream

Every command emits a sequence of events:

```
🎤 IntentDetected
↓
📋 EntitiesExtracted
↓
🔍 PlanCreated
↓
📱 DeviceConnected
↓
📱 PhoneStateVerified
↓
▶️  ExecutionStarted
↓
⚙️  StepStarted
↓
✅ StepCompleted
↓
✅ VerificationPassed
↓
🎉 ExecutionCompleted
↓
✓ All Stored in PostgreSQL
```

## Production APIs

All endpoints are fully documented with automatic OpenAPI/Swagger:

### Workflows
```
GET  /workflows                      - List workflows
GET  /workflows/{id}                 - Get workflow details
POST /workflows/{id}/cancel          - Cancel running workflow
POST /workflows/{id}/retry           - Retry failed workflow
POST /workflows/{id}/replay          - Replay with same plan
```

### Approvals
```
GET  /approvals                      - List pending approvals
POST /approvals/{id}/approve         - Approve action
POST /approvals/{id}/reject          - Reject action
```

### Audit
```
GET  /audit                          - Get audit log
GET  /audit?user_id=X&action=Y       - Filtered audit log
```

### Events
```
GET  /events/{workflow_id}           - Get all events for workflow
GET  /events/stream/{workflow_id}    - Stream events (SSE)
WS   /ws/events/{client_id}          - WebSocket real-time events
```

### Devices
```
GET  /devices                        - List connected devices
GET  /devices/{device_id}            - Get device info
```

### Metrics
```
GET  /metrics                        - Get system metrics
GET  /metrics?type=latency           - Filtered metrics
```

### Health
```
GET  /health                         - Health check
```

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env

# Key configurations:
# - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
# - ADB_PATH (path to android debug bridge)
# - OLLAMA_HOST, OLLAMA_PORT (LLM service)
# - ENCRYPTION_KEY_PATH (for credential security)
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python -c "from database.connection import init_database; init_database()"
```

### 4. Start Server

```bash
python main.py
```

Server will start on `http://localhost:8000`

## Usage Examples

### Execute a Command

```bash
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "command": "Open Instagram",
    "device_id": "device_serial"
  }'
```

### Get Workflow Status

```bash
curl http://localhost:8000/workflows/{workflow_id}
```

### Stream Events

```bash
# Server-Sent Events
curl -N http://localhost:8000/events/stream/{workflow_id}

# WebSocket
wscat -c ws://localhost:8000/ws/events/client-1
```

### Approve Action

```bash
curl -X POST http://localhost:8000/approvals/{approval_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"decided_by": "user123", "reason": "Verified recipient"}'
```

### Get Audit Log

```bash
curl "http://localhost:8000/audit?user_id=user123&action_type=WORKFLOW_COMPLETED&limit=50"
```

## Complete Workflow Example

### User says: "Open Instagram and message Guru"

The system executes this flow:

```
1. INTENT DETECTION (5s timeout)
   - Input: "Open Instagram and message Guru"
   - Output: Intent=communication, Entities=[app:instagram, contact:guru]

2. DEVICE CHECK
   - Verify device connected
   - Check lock state, battery, foreground app
   - Update device state

3. PLANNING
   - Create multi-step plan:
     - Step 1: Open Instagram
     - Step 2: Navigate to Messages
     - Step 3: Find Guru in contacts
     - Step 4: Prepare message

4. EXECUTION (with retries)
   - Execute each step with exponential backoff retry
   - Log each action to audit trail
   - Emit events in real-time

5. VERIFICATION
   - Verify Instagram opened successfully
   - Verify we're on messages screen
   - Verify Guru's chat found

6. APPROVAL
   - If confidence < threshold, request approval
   - Show preview: "Message: 'Hi Guru!'"
   - Wait for user decision

7. COMPLETION
   - Record all events
   - Store workflow record
   - Update audit log
   - Stream final event

8. RETRIEVAL
   - All data immediately available via API
   - Complete audit trail
   - All events stored
   - Metrics calculated
```

## Error Handling & Recovery

Every failure is automatically classified:

```python
# Example: Device disconnected during execution
Exception: "Device not responding"
↓
ClassifyFailure:
  Type: device_disconnected
  Recoverable: true
  Strategy: reconnect_device_and_retry
  ↓
Recovery:
  1. Wait for device
  2. Reconnect ADB
  3. Retry operation with backoff
  4. Emit recovery event
  5. Log to audit trail
```

## Secrets Management

**What is NEVER stored:**
- PIN codes
- Passwords
- Instagram tokens
- Google credentials

**What IS stored:**
- Encrypted vault references
- Access logs
- Temporary encryption keys (cleared after use)

```python
# Example: Secure PIN handling
pin_processor = PINProcessor(secret_manager)
pin_processor.accept_pin("1234")              # Encrypted immediately
pin = pin_processor.use_pin_once()            # Decrypted once for use
pin_processor.clear()                         # Memory cleared
```

## Monitoring & Observability

### Real-time Console Output

```
🎤 [10:34:25] INTENT_DETECTED: Open Instagram
📋 [10:34:26] PLAN_CREATED: 3 steps planned
📱 [10:34:27] DEVICE_CONNECTED: Device found
✅ [10:34:28] VERIFICATION_PASSED: Instagram opened
🎉 [10:34:29] EXECUTION_COMPLETED: Success in 4.2s
```

### Metrics Available

```
- Intent detection latency
- Planning duration
- Execution duration per step
- ADB call latency
- Verification duration
- Agent call performance
- Error rates by type
- Recovery success rates
```

### Event History

All events persisted and queryable:

```bash
curl "http://localhost:8000/events/{workflow_id}" | jq '.events'
[
  {
    "event_type": "intent_detected",
    "timestamp": "2024-01-15T10:34:25Z",
    "payload": {"command": "Open Instagram"}
  },
  ...
]
```

## Project Structure

```
apa-os/
├── src/
│   ├── reliability/           # Retry, circuit breaker, timeout
│   ├── audit/                 # Audit logging
│   ├── verification/          # Execution verification
│   ├── device_intelligence/   # Device detection
│   ├── understanding/         # NLU and intent
│   ├── approval_ui/           # Approval workflows
│   ├── source_visibility/     # Data provenance
│   ├── observability/         # Metrics and tracing
│   ├── governance/            # Agent permissions
│   ├── security/              # Credentials
│   ├── console/               # Event streaming
│   ├── database/              # Models and connection
│   ├── api/                   # REST endpoints
│   ├── config.py              # Configuration
│   └── orchestrator.py        # Main workflow engine
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## Performance Targets

- Intent detection: < 5 seconds
- Planning: < 10 seconds
- Execution: < 60 seconds
- Verification: < 15 seconds
- Agent calls: < 30 seconds
- Total workflow: < 90 seconds

## Logging

Logs are written to:
- Console (formatted with colors and timestamps)
- File (`apa_os.log`)

Configuration via environment:
```
LOG_LEVEL=INFO
LOG_FILE=apa_os.log
```

## Development

### Enable Debug Mode

```bash
ENVIRONMENT=development DEBUG=true python main.py
```

### Run Tests

```bash
pytest tests/ -v
```

### View API Documentation

Open browser to: `http://localhost:8000/docs`

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY main.py .
COPY .env .

EXPOSE 8000
CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - OLLAMA_HOST=ollama
    depends_on:
      - postgres
      - ollama

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=apa_os_db
```

## Support & Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql "postgresql://user:password@host:5432/apa_os"
```

### ADB Not Found
```bash
# Verify ADB path
which adb
# Update .env with correct path
```

### Ollama Not Responding
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags
```

## License

All rights reserved - APA-OS Backend

## Contributors

Built with production-grade reliability patterns and comprehensive observability.
