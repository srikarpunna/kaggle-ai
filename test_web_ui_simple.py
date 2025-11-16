#!/usr/bin/env python3
"""
ElderCare Agent - Simple Web UI Test
Tests basic Flask app setup and static files without complex dependencies.
"""

import sys
from pathlib import Path

def test_static_files():
    """Test that static files exist and have content."""
    print("=" * 60)
    print("TEST: Checking Web UI files...")
    print("=" * 60)

    required_files = {
        'Flask App': 'src/app.py',
        'HTML Template': 'src/ui/templates/index.html',
        'CSS Styles': 'src/ui/static/css/styles.css',
        'Speech API': 'src/ui/static/js/speech.js',
        'App Logic': 'src/ui/static/js/app.js'
    }

    all_exist = True
    total_size = 0

    for name, file_path in required_files.items():
        full_path = Path(file_path)
        if full_path.exists():
            size = full_path.stat().st_size
            total_size += size
            print(f"  ✓ {name:15} → {file_path:40} ({size:,} bytes)")
        else:
            print(f"  ✗ {name:15} → MISSING: {file_path}")
            all_exist = False

    print()
    print(f"  Total Web UI code: {total_size:,} bytes ({total_size / 1024:.1f} KB)")
    print()

    return all_exist


def test_databases():
    """Test that database files exist."""
    print("=" * 60)
    print("TEST: Checking database files...")
    print("=" * 60)

    db_files = {
        'Contacts DB': 'data/contacts.db',
        'Health DB': 'data/health.db',
        'Calendar DB': 'data/calendar.db',
        'Memory Bank DB': 'data/memory_bank.db'
    }

    all_exist = True
    total_size = 0

    for name, db_path in db_files.items():
        full_path = Path(db_path)
        if full_path.exists():
            size = full_path.stat().st_size
            total_size += size
            print(f"  ✓ {name:15} → {db_path:25} ({size:,} bytes)")
        else:
            print(f"  ✗ {name:15} → MISSING: {db_path}")
            all_exist = False

    print()
    print(f"  Total database size: {total_size:,} bytes ({total_size / 1024:.1f} KB)")
    print()

    return all_exist


def test_config_files():
    """Test that config files exist."""
    print("=" * 60)
    print("TEST: Checking configuration files...")
    print("=" * 60)

    config_files = {
        'Agents Config': 'config/agents.yaml',
        'Tasks Config': 'config/tasks.yaml',
        'Prompts Config': 'config/prompts.yaml',
        'UI Templates Config': 'config/ui_templates.yaml',
        'MCP Servers Config': 'config/mcp_servers.yaml'
    }

    all_exist = True
    total_size = 0

    for name, config_path in config_files.items():
        full_path = Path(config_path)
        if full_path.exists():
            size = full_path.stat().st_size
            total_size += size
            print(f"  ✓ {name:20} → {config_path:30} ({size:,} bytes)")
        else:
            print(f"  ✗ {name:20} → MISSING: {config_path}")
            all_exist = False

    print()
    print(f"  Total config size: {total_size:,} bytes ({total_size / 1024:.1f} KB)")
    print()

    return all_exist


def check_env_setup():
    """Check environment setup."""
    print("=" * 60)
    print("TEST: Checking environment setup...")
    print("=" * 60)

    env_file = Path('.env')
    env_example = Path('.env.example')

    if env_example.exists():
        print(f"  ✓ .env.example exists (template)")
    else:
        print(f"  ✗ .env.example missing")

    if env_file.exists():
        print(f"  ✓ .env exists (configured)")
        print()
        print("  ⚠️  WARNING: Make sure GEMINI_API_KEY is set in .env")
    else:
        print(f"  ⚠️  .env not found")
        print()
        print("  NEXT STEP: Copy .env.example to .env and add your GEMINI_API_KEY")
        print("  Command: cp .env.example .env")

    print()
    return True


def print_next_steps():
    """Print instructions for running the web UI."""
    print("=" * 60)
    print("NEXT STEPS: Running the Web UI")
    print("=" * 60)
    print()
    print("1. Set up environment variables:")
    print("   cp .env.example .env")
    print("   # Edit .env and add your GEMINI_API_KEY")
    print()
    print("2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("3. Start the Flask server:")
    print("   python -m src.app")
    print("   # OR")
    print("   export FLASK_APP=src.app")
    print("   flask run --host=0.0.0.0 --port=5000")
    print()
    print("4. Open in browser:")
    print("   http://localhost:5000")
    print()
    print("5. Test with voice or text:")
    print("   - Click 🎤 button to speak")
    print("   - Or type: 'Call my son'")
    print("   - Or type: 'Did I take my medication?'")
    print()


def main():
    """Run all tests."""
    print()
    print("=" * 60)
    print(" ElderCare Agent - Web UI Verification")
    print("=" * 60)
    print()

    results = []

    # Test 1: Static files
    results.append(("Web UI Files", test_static_files()))

    # Test 2: Databases
    results.append(("Databases", test_databases()))

    # Test 3: Config files
    results.append(("Config Files", test_config_files()))

    # Test 4: Environment
    results.append(("Environment", check_env_setup()))

    # Summary
    print("=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    print()

    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} {test_name}")

    print()
    print(f"  Total: {passed + failed} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print()

    if failed == 0:
        print("=" * 60)
        print("🎉 WEB UI IS READY!")
        print("=" * 60)
        print()
        print_next_steps()
        return 0
    else:
        print("=" * 60)
        print(f"⚠️  {failed} test(s) failed")
        print("=" * 60)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
