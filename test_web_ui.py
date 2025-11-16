#!/usr/bin/env python3
"""
ElderCare Agent - Web UI Test Script
Tests Flask application setup, routes, and static files.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required imports work."""
    print("=" * 60)
    print("TEST 1: Checking imports...")
    print("=" * 60)

    try:
        from flask import Flask
        print("  ✓ Flask imported")

        from flask_cors import CORS
        print("  ✓ Flask-CORS imported")

        import google.generativeai as genai
        print("  ✓ Google Generative AI imported")

        from src.main import ElderCareAgent
        print("  ✓ ElderCareAgent imported")

        print("\n✅ All imports successful!\n")
        return True
    except ImportError as e:
        print(f"\n❌ Import failed: {e}\n")
        return False


def test_app_creation():
    """Test that Flask app can be created."""
    print("=" * 60)
    print("TEST 2: Creating Flask app...")
    print("=" * 60)

    try:
        from src.app import app
        print("  ✓ Flask app created")

        # Check that app is configured
        print(f"  ✓ App name: {app.name}")
        print(f"  ✓ Template folder: {app.template_folder}")
        print(f"  ✓ Static folder: {app.static_folder}")

        print("\n✅ Flask app configuration successful!\n")
        return True, app
    except Exception as e:
        print(f"\n❌ App creation failed: {e}\n")
        return False, None


def test_routes(app):
    """Test that all routes are registered."""
    print("=" * 60)
    print("TEST 3: Checking routes...")
    print("=" * 60)

    try:
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join(rule.methods),
                'path': rule.rule
            })

        print(f"  Found {len(routes)} routes:")
        for route in routes:
            print(f"    {route['methods']:15} {route['path']:30} → {route['endpoint']}")

        # Check critical routes exist
        critical_routes = ['/', '/api/message', '/api/session/history', '/api/health']
        route_paths = [r['path'] for r in routes]

        all_exist = True
        for cr in critical_routes:
            if cr in route_paths:
                print(f"  ✓ Critical route exists: {cr}")
            else:
                print(f"  ✗ Missing critical route: {cr}")
                all_exist = False

        if all_exist:
            print("\n✅ All critical routes registered!\n")
            return True
        else:
            print("\n⚠️  Some critical routes missing!\n")
            return False

    except Exception as e:
        print(f"\n❌ Route check failed: {e}\n")
        return False


def test_static_files():
    """Test that static files exist."""
    print("=" * 60)
    print("TEST 4: Checking static files...")
    print("=" * 60)

    required_files = [
        'src/ui/templates/index.html',
        'src/ui/static/css/styles.css',
        'src/ui/static/js/speech.js',
        'src/ui/static/js/app.js'
    ]

    all_exist = True
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path:45} ({size:,} bytes)")
        else:
            print(f"  ✗ MISSING: {file_path}")
            all_exist = False

    if all_exist:
        print("\n✅ All static files present!\n")
        return True
    else:
        print("\n❌ Some static files missing!\n")
        return False


def test_database_exists():
    """Test that database files exist."""
    print("=" * 60)
    print("TEST 5: Checking database files...")
    print("=" * 60)

    db_files = [
        'data/contacts.db',
        'data/health.db',
        'data/calendar.db',
        'data/memory_bank.db'
    ]

    all_exist = True
    for db_path in db_files:
        full_path = Path(db_path)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {db_path:25} ({size:,} bytes)")
        else:
            print(f"  ✗ MISSING: {db_path}")
            all_exist = False

    if all_exist:
        print("\n✅ All database files present!\n")
        return True
    else:
        print("\n❌ Some database files missing!\n")
        return False


def test_config_files():
    """Test that config files exist."""
    print("=" * 60)
    print("TEST 6: Checking config files...")
    print("=" * 60)

    config_files = [
        'config/agents.yaml',
        'config/tasks.yaml',
        'config/prompts.yaml',
        'config/ui_templates.yaml',
        'config/mcp_servers.yaml'
    ]

    all_exist = True
    for config_path in config_files:
        full_path = Path(config_path)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {config_path:30} ({size:,} bytes)")
        else:
            print(f"  ✗ MISSING: {config_path}")
            all_exist = False

    if all_exist:
        print("\n✅ All config files present!\n")
        return True
    else:
        print("\n❌ Some config files missing!\n")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print(" ElderCare Agent - Web UI Test Suite")
    print("=" * 60)
    print("\n")

    results = []

    # Test 1: Imports
    results.append(("Imports", test_imports()))

    # Test 2: App creation
    app_result, app = test_app_creation()
    results.append(("App Creation", app_result))

    # Test 3: Routes (only if app created)
    if app:
        results.append(("Routes", test_routes(app)))
    else:
        results.append(("Routes", False))

    # Test 4: Static files
    results.append(("Static Files", test_static_files()))

    # Test 5: Databases
    results.append(("Databases", test_database_exists()))

    # Test 6: Config files
    results.append(("Config Files", test_config_files()))

    # Summary
    print("\n")
    print("=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"  Total: {passed + failed} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print()

    if failed == 0:
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! Web UI is ready to run!")
        print("=" * 60)
        print()
        print("To start the web application:")
        print("  1. Copy .env.example to .env and add your GEMINI_API_KEY")
        print("  2. Run: python -m flask run --host=0.0.0.0 --port=5000")
        print("  3. Open: http://localhost:5000")
        print()
        return 0
    else:
        print("=" * 60)
        print(f"⚠️  {failed} test(s) failed. Please fix before running.")
        print("=" * 60)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
