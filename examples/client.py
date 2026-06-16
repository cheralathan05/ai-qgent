"""
Example Client Usage
Demonstrates how to interact with the APA-OS Backend API
"""

import asyncio
import aiohttp
import json
import websockets
from datetime import datetime


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


async def example_1_simple_command():
    """Example 1: Execute a simple command"""
    print("=" * 60)
    print("Example 1: Simple Command Execution")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Create workflow
        payload = {
            "user_id": "user123",
            "command": "Open Instagram",
            "device_id": "device_serial_123",
            "voice_input": False,
        }
        
        print(f"\n📤 Executing command: {payload['command']}")
        
        async with session.post(f"{BASE_URL}/workflows", json=payload) as resp:
            result = await resp.json()
            workflow_id = result.get("workflow_id")
            print(f"✓ Workflow created: {workflow_id}")
            
            # Poll for completion
            for i in range(10):
                await asyncio.sleep(2)
                
                async with session.get(f"{BASE_URL}/workflows/{workflow_id}") as status_resp:
                    status = await status_resp.json()
                    print(f"  Status: {status['status']}")
                    
                    if status['status'] in ['completed', 'failed']:
                        print(f"\n✓ Result: {status}")
                        return status


async def example_2_stream_events():
    """Example 2: Stream real-time events"""
    print("\n" + "=" * 60)
    print("Example 2: Real-time Event Streaming")
    print("=" * 60)
    
    workflow_id = "example_workflow_id"
    
    print(f"\n🔌 Connecting to event stream for {workflow_id}...")
    
    try:
        async with websockets.connect(f"{WS_URL}/ws/events/client-1") as websocket:
            print("✓ Connected to WebSocket")
            
            # Receive events
            for i in range(10):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    event = json.loads(message)
                    
                    timestamp = event.get("timestamp", "")
                    event_type = event.get("event_type", "")
                    payload = event.get("payload", {})
                    
                    print(f"  📨 [{timestamp}] {event_type}: {payload}")
                
                except asyncio.TimeoutError:
                    print("  ⏱️  No events received (timeout)")
                    break
    
    except Exception as e:
        print(f"✗ Error: {e}")


async def example_3_approval_workflow():
    """Example 3: Workflow requiring approval"""
    print("\n" + "=" * 60)
    print("Example 3: Approval Workflow")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # List pending approvals
        print("\n📋 Fetching pending approvals...")
        
        async with session.get(f"{BASE_URL}/approvals") as resp:
            approvals = await resp.json()
            
            if not approvals.get("approvals"):
                print("  No pending approvals")
                return
            
            for approval in approvals["approvals"]:
                print(f"\n  Approval ID: {approval['id']}")
                print(f"  Type: {approval['type']}")
                print(f"  Preview: {approval['preview']}")
                print(f"  Explanation: {approval['explanation']}")
                
                # Approve
                approval_id = approval['id']
                payload = {
                    "decided_by": "user123",
                    "reason": "Verified recipient address"
                }
                
                async with session.post(
                    f"{BASE_URL}/approvals/{approval_id}/approve",
                    json=payload
                ) as approve_resp:
                    result = await approve_resp.json()
                    print(f"  ✓ Approved: {result}")


async def example_4_audit_log():
    """Example 4: View audit log"""
    print("\n" + "=" * 60)
    print("Example 4: Audit Log")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        print("\n📜 Fetching audit log...")
        
        params = {
            "user_id": "user123",
            "limit": 20,
        }
        
        async with session.get(f"{BASE_URL}/audit", params=params) as resp:
            audit_data = await resp.json()
            
            print(f"  Total events: {audit_data['total']}")
            
            for event in audit_data.get("events", [])[:5]:
                print(f"\n  • {event['action_type']}")
                print(f"    Resource: {event['resource_type']} ({event['resource_id']})")
                print(f"    Result: {event['result']}")
                print(f"    Time: {event['timestamp']}")


async def example_5_device_info():
    """Example 5: Get device information"""
    print("\n" + "=" * 60)
    print("Example 5: Device Information")
    print("=" * 60)
    
    device_id = "device_serial_123"
    
    async with aiohttp.ClientSession() as session:
        print(f"\n📱 Getting device info for {device_id}...")
        
        async with session.get(f"{BASE_URL}/devices/{device_id}") as resp:
            if resp.status == 200:
                device_info = await resp.json()
                
                print(f"  Connected: {device_info['is_connected']}")
                print(f"  Locked: {device_info['is_locked']}")
                print(f"  Battery: {device_info['battery_level']}%")
                print(f"  Foreground App: {device_info['foreground_app']}")
                print(f"  Model: {device_info['model_name']}")
                print(f"  Android: {device_info['android_version']}")
                print(f"  Installed Apps: {len(device_info['installed_apps'])} apps")
                print(f"  Capabilities: {', '.join(device_info['available_capabilities'])}")
            else:
                print(f"✗ Error: {resp.status}")


async def example_6_workflow_lifecycle():
    """Example 6: Complete workflow lifecycle"""
    print("\n" + "=" * 60)
    print("Example 6: Complete Workflow Lifecycle")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Create workflow
        print("\n1️⃣  Creating workflow...")
        create_payload = {
            "user_id": "user123",
            "command": "Open Instagram and message Guru",
            "device_id": "device_serial_123",
            "voice_input": True,
        }
        
        async with session.post(f"{BASE_URL}/workflows", json=create_payload) as resp:
            workflow_data = await resp.json()
            workflow_id = workflow_data.get("workflow_id")
            print(f"   ✓ Created: {workflow_id}")
        
        # 2. Get workflow details
        print("\n2️⃣  Getting workflow details...")
        async with session.get(f"{BASE_URL}/workflows/{workflow_id}") as resp:
            details = await resp.json()
            print(f"   Status: {details['status']}")
            print(f"   Intent: {details['intent']}")
        
        # 3. Get events
        print("\n3️⃣  Getting workflow events...")
        async with session.get(f"{BASE_URL}/events/{workflow_id}") as resp:
            events_data = await resp.json()
            print(f"   Total events: {events_data['total']}")
            for event in events_data.get("events", [])[:3]:
                print(f"     • {event['event_type']}")
        
        # 4. Check for approvals
        print("\n4️⃣  Checking for approvals...")
        async with session.get(f"{BASE_URL}/approvals") as resp:
            approvals_data = await resp.json()
            print(f"   Pending approvals: {len(approvals_data.get('approvals', []))}")
        
        # 5. Get audit trail
        print("\n5️⃣  Getting audit trail...")
        async with session.get(f"{BASE_URL}/audit", params={"workflow_id": workflow_id}) as resp:
            audit_data = await resp.json()
            print(f"   Audit events: {audit_data['total']}")


async def example_7_retry_workflow():
    """Example 7: Retry a failed workflow"""
    print("\n" + "=" * 60)
    print("Example 7: Retry Failed Workflow")
    print("=" * 60)
    
    workflow_id = "failed_workflow_id"
    
    async with aiohttp.ClientSession() as session:
        print(f"\n🔄 Retrying workflow {workflow_id}...")
        
        async with session.post(
            f"{BASE_URL}/workflows/{workflow_id}/retry"
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                new_workflow_id = result.get("new_workflow_id")
                print(f"  ✓ Retrying as: {new_workflow_id}")
                print(f"    Original: {result['original_workflow_id']}")
                print(f"    Status: {result['status']}")
            else:
                print(f"  ✗ Error: {resp.status}")


async def example_8_metrics():
    """Example 8: Get system metrics"""
    print("\n" + "=" * 60)
    print("Example 8: System Metrics")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        print("\n📊 Fetching system metrics...")
        
        async with session.get(f"{BASE_URL}/metrics", params={"limit": 10}) as resp:
            metrics_data = await resp.json()
            
            print(f"  Total metrics: {metrics_data['total']}")
            
            for metric in metrics_data.get("metrics", [])[:5]:
                print(f"\n  • {metric['name']}")
                print(f"    Value: {metric['value']} {metric['unit']}")
                print(f"    Type: {metric['type']}")


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  APA-OS Backend - Example Client Usage  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    # Run examples
    await example_1_simple_command()
    # await example_2_stream_events()
    await example_3_approval_workflow()
    await example_4_audit_log()
    await example_5_device_info()
    await example_6_workflow_lifecycle()
    # await example_7_retry_workflow()
    await example_8_metrics()
    
    print("\n" + "=" * 60)
    print("✓ All examples completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
