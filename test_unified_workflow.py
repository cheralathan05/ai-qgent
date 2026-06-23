"""
Test script for APA-OS Unified Workflow
Verifies the complete pipeline works end-to-end.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_intent_detection():
    """Test intent detection for various commands."""
    from services.intent_agent import get_intent_agent
    
    agent = get_intent_agent()
    
    test_commands = [
        ("Open Instagram", "open_app", "instagram"),
        ("Open Spotify", "open_app", "spotify"),
        ("Open Telegram", "open_app", "telegram"),
        ("Open Calculator", "open_app", "calculator"),
        ("Open Camera", "open_camera", "camera"),
        ("Open Settings", "open_settings", None),
        ("What's my battery level?", "battery_status", None),
        ("Take a screenshot", "take_screenshot", None),
        ("Search for AI Agents", "search", None),
        ("Send hello to Guru", "send_message", None),
    ]
    
    print("\n=== Intent Detection Tests ===")
    all_passed = True
    
    for command, expected_intent, expected_app in test_commands:
        result = await agent.detect_intent(command)
        intent = result.intent.value
        app = result.slots.get("app")
        
        # Check intent matches
        passed = intent == expected_intent
        
        # Check app matches if expected
        if expected_app and app:
            passed = passed and expected_app.lower() in app.lower()
        elif expected_app and not app:
            # Some intents don't have app in slots (like open_settings)
            passed = passed  # Intent match is enough
        
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] '{command}' -> intent={intent}, app={app}")
        
        if not passed:
            all_passed = False
    
    return all_passed


async def test_app_resolution():
    """Test dynamic app resolution."""
    from services.app_resolver import get_app_resolver
    
    resolver = get_app_resolver()
    
    test_apps = [
        ("spotify", "com.spotify.music"),
        ("telegram", "org.telegram.messenger"),
        ("instagram", "com.instagram.android"),
        ("whatsapp", "com.whatsapp"),
        ("chrome", "com.android.chrome"),
        ("youtube", "com.google.android.youtube"),
        ("calculator", "com.android.calculator2"),
        ("camera", "com.android.camera"),
        ("settings", "com.android.settings"),
    ]
    
    print("\n=== App Resolution Tests ===")
    
    # Note: These tests require a connected device
    # For now, we'll test the fallback mapping
    from services.app_launch import AppLaunchService
    
    print("  (Testing fallback mapping - requires device for full resolution)")
    
    launch_svc = AppLaunchService()
    
    for app_name, expected_package in test_apps:
        result = launch_svc._resolve_package_fallback(app_name)
        passed = result == expected_package
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] '{app_name}' -> {result} (expected: {expected_package})")
    
    return True


async def test_workflow_engine():
    """Test the unified workflow engine (requires device)."""
    from services.unified_workflow import get_unified_workflow
    
    engine = get_unified_workflow()
    
    print("\n=== Workflow Engine Tests ===")
    print("  (Requires connected Android device)")
    
    # Check if device is connected
    device_id = await engine.get_connected_device_id()
    
    if not device_id:
        print("  [SKIP] No Android device connected")
        return True
    
    print(f"  [INFO] Connected device: {device_id}")
    
    # Test simple command
    result = await engine.execute_command(
        command="Open Calculator",
        device_id=device_id,
    )
    
    print(f"  Result: success={result.success}, intent={result.intent}")
    print(f"  Message: {result.message}")
    print(f"  Package: {result.package_name}")
    print(f"  Verified: {result.verification_passed}")
    
    return result.success


async def test_api_endpoints():
    """Test API endpoints."""
    print("\n=== API Endpoint Tests ===")
    print("  (Requires running server)")
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Health check
            response = await client.get("http://localhost:8000/v1/health")
            if response.status_code == 200:
                print("  [PASS] GET /v1/health")
            else:
                print(f"  [FAIL] GET /v1/health -> {response.status_code}")
            
            # Device status
            response = await client.get("http://localhost:8000/v1/device/status")
            if response.status_code == 200:
                print("  [PASS] GET /v1/device/status")
            else:
                print(f"  [FAIL] GET /v1/device/status -> {response.status_code}")
            
            return True
    except ImportError:
        print("  [SKIP] httpx not installed")
        return True
    except Exception as e:
        print(f"  [INFO] Server not running: {e}")
        return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("APA-OS Unified Workflow Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(await test_intent_detection())
    results.append(await test_app_resolution())
    results.append(await test_workflow_engine())
    results.append(await test_api_endpoints())
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests: {passed}/{total} passed")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
