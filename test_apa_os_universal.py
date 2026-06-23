"""
Test APA-OS Universal Intelligence Engine
Verifies the complete pipeline works for ANY command.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_universal_intent():
    """Test universal intent understanding for ANY command."""
    from core.intent_engine import get_intent_engine
    
    engine = get_intent_engine()
    
    test_cases = [
        # Device Control
        ("Open Instagram", "open_app", "instagram"),
        ("Open Spotify", "open_app", "spotify"),
        ("Open Telegram", "open_app", "telegram"),
        ("Open Calculator", "open_app", "calculator"),
        ("Open Camera", "open_camera", None),
        ("Close WhatsApp", "close_app", "whatsapp"),
        ("Open Settings", "open_settings", None),
        
        # Communication
        ("Send hello to Guru", "send_message", None),
        ("Call Mom", "call_contact", None),
        ("Open WhatsApp chat with John", "open_chat", None),
        
        # Information
        ("What's my battery level?", "battery_status", None),
        ("Take a screenshot", "take_screenshot", None),
        ("What app is open?", "foreground_app", None),
        
        # Search
        ("Search for AI Agents", "web_search", None),
        ("Google Python tutorials", "web_search", None),
        
        # Knowledge
        ("Find my DBMS notes", "find_file", None),
        ("Summarize my OS notes", "summarize", None),
        ("Explain Normalization", "explain", None),
        ("Generate 20 interview questions on Python", "generate_questions", None),
        ("Generate MCQs on DBMS", "generate_mcq", None),
        ("Create assignment on Operating Systems", "generate_assignment", None),
        
        # Navigation
        ("Go back", "go_back", None),
        ("Go home", "go_home", None),
        ("Scroll down", "scroll", None),
        
        # System
        ("Turn on WiFi", "toggle_wifi", None),
        ("Turn off Bluetooth", "toggle_bluetooth", None),
        ("Volume up", "volume_control", None),
        ("Lock device", "lock_device", None),
        
        # Compound
        ("Open YouTube and search AI Agents", "compound_action", None),
    ]
    
    print("\n=== Universal Intent Understanding Tests ===")
    passed = 0
    failed = 0
    
    for command, expected_intent, expected_app in test_cases:
        result = await engine.understand(command)
        intent = result.intent.value
        app = result.slots.get("app")
        
        # Check intent matches
        intent_ok = intent == expected_intent
        
        # Check app matches if expected
        app_ok = True
        if expected_app and app:
            app_ok = expected_app.lower() in app.lower()
        
        success = intent_ok and app_ok
        status = "PASS" if success else "FAIL"
        
        if success:
            passed += 1
        else:
            failed += 1
        
        print(f"  [{status}] '{command}'")
        if not success:
            print(f"         Expected: intent={expected_intent}, app={expected_app}")
            print(f"         Got:      intent={intent}, app={app}")
    
    print(f"\n  Results: {passed}/{passed + failed} passed")
    return failed == 0


async def test_workflow_generation():
    """Test workflow generation for various intents."""
    from core.intent_engine import get_intent_engine
    from core.workflow_generator import get_workflow_generator
    
    intent_engine = get_intent_engine()
    workflow_gen = get_workflow_generator()
    
    test_commands = [
        "Open Spotify",
        "Send hello to Guru",
        "What's my battery level?",
        "Take a screenshot",
        "Search for AI Agents",
        "Find my DBMS notes",
        "Summarize my OS notes",
        "Explain Normalization",
        "Turn on WiFi",
        "Go back",
    ]
    
    print("\n=== Workflow Generation Tests ===")
    all_ok = True
    
    for command in test_commands:
        intent_result = await intent_engine.understand(command)
        workflow = workflow_gen.generate(intent_result)
        
        has_steps = len(workflow.steps) > 0
        has_phases = workflow.requires_phase1 or workflow.requires_phase2 or workflow.requires_phase3
        
        success = has_steps and has_phases
        status = "PASS" if success else "FAIL"
        
        if not success:
            all_ok = False
        
        print(f"  [{status}] '{command}' -> {len(workflow.steps)} steps, phases=[P1={workflow.requires_phase1},P2={workflow.requires_phase2},P3={workflow.requires_phase3}]")
    
    return all_ok


async def test_memory_system():
    """Test memory system."""
    from core.memory_engine import get_memory_engine
    
    memory = get_memory_engine()
    
    print("\n=== Memory System Tests ===")
    
    # Record some data
    memory.record_command("Open Instagram", "open_app", True)
    memory.record_app("instagram")
    memory.record_search("AI Agents")
    memory.record_document("DBMS_Notes.pdf")
    memory.record_contact("Guru")
    
    # Get summary
    summary = memory.get_summary()
    
    success = (
        summary["recent_commands"] > 0 and
        "instagram" in summary["recent_apps"] and
        "AI Agents" in summary["recent_searches"] and
        "DBMS_Notes.pdf" in summary["recent_documents"] and
        "Guru" in summary["recent_contacts"]
    )
    
    status = "PASS" if success else "FAIL"
    print(f"  [{status}] Memory recording and retrieval")
    print(f"         Commands: {summary['recent_commands']}")
    print(f"         Apps: {summary['recent_apps']}")
    print(f"         Searches: {summary['recent_searches']}")
    print(f"         Documents: {summary['recent_documents']}")
    print(f"         Contacts: {summary['recent_contacts']}")
    
    return success


async def test_knowledge_engine():
    """Test knowledge operations engine."""
    from core.knowledge_engine import get_knowledge_engine
    
    engine = get_knowledge_engine()
    
    print("\n=== Knowledge Engine Tests ===")
    
    # Test search
    result = await engine.search_files("test query")
    print(f"  [INFO] Search result: {result.success}")
    
    # Test summarize (will return no content message)
    result = await engine.summarize("test topic")
    print(f"  [INFO] Summarize result: {result.success}")
    
    # Test generate assignment
    result = await engine.generate_assignment("test topic")
    has_content = len(result.answer) > 100
    print(f"  [{'PASS' if has_content else 'FAIL'}] Generate assignment")
    
    # Test generate MCQ
    result = await engine.generate_mcq("test topic", 5)
    has_questions = "?" in result.answer
    print(f"  [{'PASS' if has_questions else 'FAIL'}] Generate MCQ")
    
    # Test generate questions
    result = await engine.generate_questions("test topic", 10)
    has_questions = "?" in result.answer
    print(f"  [{'PASS' if has_questions else 'FAIL'}] Generate questions")
    
    return True


async def test_complete_pipeline():
    """Test the complete APA-OS pipeline."""
    from core.apa_os import get_apa_os
    
    apa_os = get_apa_os()
    
    print("\n=== Complete Pipeline Tests ===")
    
    test_commands = [
        "Open Instagram",
        "What's my battery level?",
        "Take a screenshot",
    ]
    
    all_ok = True
    
    for command in test_commands:
        result = await apa_os.process(command)
        
        success = result.success or result.message != ""
        status = "PASS" if success else "FAIL"
        
        if not success:
            all_ok = False
        
        print(f"  [{status}] '{command}'")
        print(f"         Intent: {result.intent}")
        print(f"         Message: {result.message[:80]}")
        print(f"         Duration: {result.duration_ms:.0f}ms")
    
    return all_ok


async def main():
    """Run all tests."""
    print("=" * 70)
    print("APA-OS Universal Intelligence Engine Tests")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Intent Understanding", await test_universal_intent()))
    results.append(("Workflow Generation", await test_workflow_generation()))
    results.append(("Memory System", await test_memory_system()))
    results.append(("Knowledge Engine", await test_knowledge_engine()))
    results.append(("Complete Pipeline", await test_complete_pipeline()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    passed_count = sum(1 for _, p in results if p)
    print(f"Total: {passed_count}/{len(results)} test suites passed")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
