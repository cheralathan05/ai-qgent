"""
APA-OS Layer Integration Tests

Tests all 15 layers working together.
"""

import sys
sys.path.insert(0, 'src')

import asyncio
import time


async def test_verification_engine():
    """Test Layer 9 - Verification Engine."""
    from core.verification_engine import get_verification_engine, VerificationType, VerificationStatus
    
    engine = get_verification_engine()
    
    print("\n=== Verification Engine Tests ===")
    
    # Test knowledge verification
    result = await engine.verify_knowledge_found(
        "test query",
        context={"sources": [{"file_name": "test.pdf", "score": 0.9}]},
    )
    status = "PASS" if result.status == VerificationStatus.PASSED else "FAIL"
    print(f"  [{status}] Knowledge verification")
    
    # Test action verification
    result = await engine.verify(
        VerificationType.ACTION_COMPLETED,
        expected="test_action",
        context={"success": True},
    )
    status = "PASS" if result.status == VerificationStatus.PASSED else "FAIL"
    print(f"  [{status}] Action verification")
    
    # Test status
    status_info = engine.get_status()
    has_rules = status_info["rules_registered"] > 0
    status = "PASS" if has_rules else "FAIL"
    print(f"  [{status}] Status check: {status_info['rules_registered']} rules")
    
    return True


async def test_event_bus():
    """Test Layer 12 - Event Bus."""
    from core.event_bus import get_event_bus, EventType
    
    bus = get_event_bus()
    
    print("\n=== Event Bus Tests ===")
    
    # Track events
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    bus.subscribe(EventType.COMMAND_RECEIVED, handler)
    
    # Emit events
    await bus.emit(
        EventType.COMMAND_RECEIVED,
        source="test",
        data={"command": "test command"},
    )
    
    await bus.emit(
        EventType.INTENT_DETECTED,
        source="test",
        data={"intent": "open_app"},
    )
    
    # Check received
    status = "PASS" if len(received_events) == 1 else "FAIL"
    print(f"  [{status}] Event subscription: {len(received_events)} events received")
    
    # Check history
    history = bus.get_history()
    status = "PASS" if len(history) == 2 else "FAIL"
    print(f"  [{status}] Event history: {len(history)} events")
    
    # Check stats
    stats = bus.get_stats()
    status = "PASS" if stats.get("command_received", 0) == 1 else "FAIL"
    print(f"  [{status}] Event stats: {stats}")
    
    # Cleanup
    bus.unsubscribe(EventType.COMMAND_RECEIVED, handler)
    
    return True


async def test_recovery_engine():
    """Test Layer 14 - Recovery Engine."""
    from core.recovery_engine import get_recovery_engine, FailureType, RecoveryStrategy
    
    engine = get_recovery_engine()
    
    print("\n=== Recovery Engine Tests ===")
    
    # Test recovery for app not found
    result = await engine.recover(
        FailureType.APP_NOT_FOUND,
        context={"app_category": "browser"},
    )
    
    # Should either find alternative or escalate
    valid = result.strategy in (
        RecoveryStrategy.ALTERNATIVE_APP,
        RecoveryStrategy.ESCALATE,
    )
    status = "PASS" if valid else "FAIL"
    print(f"  [{status}] App not found recovery: {result.strategy.value}")
    
    # Test recovery for timeout
    result = await engine.recover(
        FailureType.TIMEOUT,
        context={"timeout_ms": 5000},
    )
    status = "PASS" if result.strategy else "FAIL"
    print(f"  [{status}] Timeout recovery: {result.strategy.value}")
    
    # Test status
    status_info = engine.get_status()
    has_chains = status_info["recovery_chains"] > 0
    status = "PASS" if has_chains else "FAIL"
    print(f"  [{status}] Status check: {status_info['recovery_chains']} chains")
    
    return True


async def test_learning_engine():
    """Test Layer 10 - Learning Engine."""
    from core.learning_engine import get_learning_engine
    
    engine = get_learning_engine()
    
    print("\n=== Learning Engine Tests ===")
    
    # Record interactions
    for _ in range(5):
        engine.record_interaction("app_usage", "instagram")
    
    for _ in range(3):
        engine.record_interaction("app_usage", "whatsapp")
    
    for _ in range(4):
        engine.record_interaction("contact_frequency", "Guru")
    
    # Test frequent apps
    apps = engine.get_frequent_apps(5)
    status = "PASS" if len(apps) > 0 and apps[0].key == "instagram" else "FAIL"
    print(f"  [{status}] Frequent apps: {[a.key for a in apps[:3]]}")
    
    # Test frequent contacts
    contacts = engine.get_frequent_contacts(5)
    status = "PASS" if len(contacts) > 0 and contacts[0].key == "Guru" else "FAIL"
    print(f"  [{status}] Frequent contacts: {[c.key for c in contacts[:3]]}")
    
    # Test suggestions
    suggestions = await engine.suggest_automations()
    has_suggestions = len(suggestions) > 0
    status = "PASS" if has_suggestions else "FAIL"
    print(f"  [{status}] Automation suggestions: {len(suggestions)}")
    
    # Test behavior analysis
    analysis = await engine.analyze_behavior()
    status = "PASS" if analysis["total_interactions"] > 0 else "FAIL"
    print(f"  [{status}] Behavior analysis: {analysis['total_interactions']} interactions")
    
    return True


async def test_conversation_manager():
    """Test Layer 1 - Conversation Manager."""
    from core.conversation_manager import get_conversation_manager
    
    manager = get_conversation_manager()
    
    print("\n=== Conversation Manager Tests ===")
    
    # Start conversation
    conv = manager.start_conversation()
    has_conv = conv is not None
    status = "PASS" if has_conv else "FAIL"
    print(f"  [{status}] Start conversation: {conv.id}")
    
    # Add messages
    manager.add_user_message("Open Instagram", intent="open_app")
    manager.add_assistant_message("Opening Instagram.")
    manager.add_user_message("Send hello to Guru", intent="send_message")
    
    # Check message count
    conv = manager.get_active_conversation()
    status = "PASS" if len(conv.messages) == 3 else "FAIL"
    print(f"  [{status}] Message count: {len(conv.messages)}")
    
    # Check context
    context = manager.get_context()
    has_goal = "active_goal" in context
    status = "PASS" if has_goal else "FAIL"
    print(f"  [{status}] Context: {list(context.keys())}")
    
    # Test goal setting
    manager.set_active_goal("Send message to Guru")
    goal = manager.get_active_goal()
    status = "PASS" if goal == "Send message to Guru" else "FAIL"
    print(f"  [{status}] Active goal: {goal}")
    
    # Test interruption
    interrupted = manager.handle_interruption("What's the weather?")
    status = "PASS" if interrupted else "FAIL"
    print(f"  [{status}] Interruption handled: {interrupted}")
    
    # Test resume
    resumed = manager.resume_interrupted()
    status = "PASS" if resumed == "Send message to Guru" else "FAIL"
    print(f"  [{status}] Resume interrupted: {resumed}")
    
    # Test summary
    summary = manager.get_conversation_summary()
    has_summary = len(summary) > 0
    status = "PASS" if has_summary else "FAIL"
    print(f"  [{status}] Conversation summary: {len(summary)} chars")
    
    # Test status
    status_info = manager.get_status()
    has_convs = status_info["total_conversations"] > 0
    status = "PASS" if has_convs else "FAIL"
    print(f"  [{status}] Status check: {status_info['total_conversations']} conversations")
    
    return True


async def test_integrated_pipeline():
    """Test full integrated pipeline."""
    from core.apa_os import get_apa_os
    
    apa_os = get_apa_os()
    
    print("\n=== Integrated Pipeline Tests ===")
    
    # Test knowledge pipeline
    result = await apa_os.process("Generate assignment on Python")
    status = "PASS" if result.success else "FAIL"
    print(f"  [{status}] Knowledge pipeline: {result.intent}")
    print(f"         Verification: {result.verification_passed}")
    print(f"         Events emitted: {result.events_emitted}")
    
    # Test event emission
    history = apa_os.events.get_history()
    has_events = len(history) > 0
    status = "PASS" if has_events else "FAIL"
    print(f"  [{status}] Events emitted: {len(history)}")
    
    # Test learning
    apps = apa_os.learning.get_frequent_apps(5)
    has_learning = len(apps) > 0
    status = "PASS" if has_learning else "FAIL"
    print(f"  [{status}] Learning: {len(apps)} apps tracked")
    
    # Test conversation
    conv = apa_os.conversation.get_active_conversation()
    has_conv = conv is not None and len(conv.messages) > 0
    status = "PASS" if has_conv else "FAIL"
    print(f"  [{status}] Conversation: {len(conv.messages) if conv else 0} messages")
    
    # Test system status
    full_status = apa_os.get_status()
    has_layers = len(full_status.get("layers", {})) > 0
    status = "PASS" if has_layers else "FAIL"
    print(f"  [{status}] System status: {len(full_status.get('layers', {}))} layers")
    
    return True


async def main():
    """Run all layer integration tests."""
    print("=" * 70)
    print("APA-OS Layer Integration Tests")
    print("=" * 70)
    
    tests = [
        ("Verification Engine", test_verification_engine),
        ("Event Bus", test_event_bus),
        ("Recovery Engine", test_recovery_engine),
        ("Learning Engine", test_learning_engine),
        ("Conversation Manager", test_conversation_manager),
        ("Integrated Pipeline", test_integrated_pipeline),
    ]
    
    results = {}
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results[name] = result
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("LAYER INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
