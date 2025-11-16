# 📘 ElderCare Agent - Complete Setup Guide

This guide will walk you through setting up the ElderCare Agent system from scratch.

## ⏱️ Estimated Time: 20-30 minutes

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.10 or higher installed
- [ ] Git installed
- [ ] A Google account (for Gemini API and Calendar API)
- [ ] Text editor or IDE
- [ ] Terminal/Command Prompt access

---

## 🚀 Step-by-Step Setup

### Step 1: Clone the Repository (2 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/eldercare-agent.git

# Navigate to the project directory
cd eldercare-agent

# Verify the structure
ls -la
```

You should see:
```
config/
data/
src/
tests/
docs/
requirements.txt
README.md
.env.example
```

---

### Step 2: Set Up Python Environment (3 minutes)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (you should see (venv) in your prompt)
which python  # Should show path to venv/bin/python
```

---

### Step 3: Install Dependencies (2 minutes)

```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list | grep google-generativeai
```

Expected output: `google-generativeai  x.x.x`

---

### Step 4: Get Gemini API Key (FREE) (5 minutes)

1. **Go to Google AI Studio:**
   - Visit: https://makersuite.google.com/app/apikey

2. **Create API Key:**
   - Click "Create API Key"
   - Select or create a Google Cloud project
   - Copy the API key (starts with `AIza...`)

3. **Save your API key:**
   ```bash
   # Copy the example env file
   cp .env.example .env

   # Open .env in your editor
   nano .env  # or vim, code, etc.
   ```

4. **Paste your API key:**
   ```env
   GEMINI_API_KEY=AIzaSy...YOUR_ACTUAL_KEY...
   ```

5. **Save and close the file**

---

### Step 5: Set Up Google Calendar API (OPTIONAL) (10 minutes)

**Note:** You can skip this step for initial testing. The system will work without it.

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create or select a project:**
   - Click "Select a project" dropdown
   - Click "NEW PROJECT"
   - Name it "ElderCare Agent"
   - Click "CREATE"

3. **Enable Google Calendar API:**
   - In the search bar, type "Calendar API"
   - Click "Google Calendar API"
   - Click "ENABLE"

4. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "OAuth client ID"
   - If prompted, configure the OAuth consent screen:
     - User Type: External
     - App name: ElderCare Agent
     - User support email: your email
     - Developer contact: your email
     - Save and continue through all steps
   - Application type: "Desktop app"
   - Name: "ElderCare Agent Client"
   - Click "CREATE"

5. **Download credentials:**
   - Click the download button (⬇️) next to your new OAuth client
   - Save the file as `google_calendar_credentials.json`
   - Move it to the `config/` folder:
     ```bash
     mv ~/Downloads/client_secret_*.json config/google_calendar_credentials.json
     ```

---

### Step 6: Initialize Databases (2 minutes)

```bash
# Run the database initialization script
python src/core/database.py
```

Expected output:
```
Initializing ElderCare Agent databases...
Initializing contacts database: data/contacts.db
Contacts database initialized
Initializing health database: data/health.db
Health database initialized
Initializing calendar database: data/calendar.db
Calendar database initialized
Initializing memory database: data/memory_bank.db
Memory database initialized
Seeding demo data for user: margaret_thompson
Seeded 4 contacts
Seeded 3 medications
Seeded 1 doctors
✓ Databases initialized and seeded successfully!
```

Verify databases were created:
```bash
ls -lh data/*.db
```

You should see:
- `contacts.db`
- `health.db`
- `calendar.db`
- `memory_bank.db`

---

### Step 7: Test the Configuration System (2 minutes)

```bash
# Test that all configs load correctly
python src/core/config_loader.py
```

Expected output:
```
Loading configurations...

✓ Loaded 5 agents:
  - Orchestrator Agent
  - Communication Agent
  - Health Agent
  - UI Generator Agent
  - Memory Agent

✓ Loaded 3 tasks:
  - Video Call Family
  - Medication Reminders
  - Doctor Appointments

✓ Loaded 6 UI templates:
  - Video Call Interface
  - Medication Reminder Interface
  - Doctor Appointment Interface
  - Yes/No Confirmation Interface
  - Success Confirmation Interface
  - Error Message Interface

✓ Loaded 3 MCP servers:
  - Contacts MCP Server
  - Health MCP Server
  - Calendar MCP Server

✓ Testing prompt retrieval:
  Greeting prompt length: XXX chars

✓ Configuration system working correctly!
```

---

### Step 8: Test the Orchestrator Agent (3 minutes)

```bash
# Test the Orchestrator Agent with Gemini
python src/agents/orchestrator.py
```

Expected output:
```
Testing Orchestrator Agent with Gemini...

============================================================
User: Call my son
============================================================
Intent: VIDEO_CALL
Confidence: 0.95
Entities: {'person': 'son'}
→ Routing to: communication agent

============================================================
User: I need to take my medication
============================================================
Intent: MEDICATION
Confidence: 0.98
Entities: {}
→ Routing to: health agent

[... more test outputs ...]
```

If you see this, **your system is working!** ✅

---

## 🎯 Next Steps

### Option 1: Run the Full Application (Coming Soon)

```bash
python src/main.py
```

Then open your browser to: http://localhost:5000

### Option 2: Run Individual Components

Test each agent individually:

```bash
# Test Communication Agent
python src/agents/communication.py

# Test Health Agent
python src/agents/health.py

# Test UI Generator
python src/agents/ui_generator.py
```

### Option 3: Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=src tests/
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'google.generativeai'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: "GEMINI_API_KEY not found in environment"

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# If not, copy from example
cp .env.example .env

# Edit .env and add your API key
nano .env
```

---

### Issue: "Config directory not found"

**Solution:**
```bash
# Make sure you're in the project root
pwd  # Should end with /eldercare-agent

# Check if config directory exists
ls -la config/

# If not, you may need to re-clone the repository
```

---

### Issue: "Database file not found"

**Solution:**
```bash
# Reinitialize databases
python src/core/database.py

# Verify creation
ls -lh data/*.db
```

---

### Issue: Google Calendar API not working

**Solution:**
1. Make sure you downloaded `client_secret_*.json` from Google Cloud Console
2. Rename it to `google_calendar_credentials.json`
3. Place it in the `config/` folder
4. On first run, a browser window will open for OAuth consent
5. Allow the application to access your calendar

---

### Issue: Import errors when running scripts

**Solution:**
```bash
# Add the project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root with module syntax
python -m src.core.config_loader
python -m src.agents.orchestrator
```

---

## ✅ Verification Checklist

Before proceeding to development, verify:

- [ ] Python virtual environment is activated
- [ ] All dependencies are installed (`pip list`)
- [ ] `.env` file exists with your `GEMINI_API_KEY`
- [ ] All 4 SQLite databases are created in `data/`
- [ ] Configuration loader runs without errors
- [ ] Orchestrator Agent test runs successfully
- [ ] (Optional) Google Calendar credentials are configured

---

## 📚 Next: Read the Documentation

- [README.md](../README.md) - Project overview
- [Architecture Documentation](./ARCHITECTURE.md) - System design details
- [API Documentation](./API.md) - API endpoints and usage

---

## 🆘 Getting Help

If you're stuck:

1. Check the troubleshooting section above
2. Review error messages carefully
3. Check the logs in `logs/` folder
4. Open an issue on GitHub with:
   - Your OS (Windows/Mac/Linux)
   - Python version (`python --version`)
   - Full error message
   - Steps to reproduce

---

## 🎉 Success!

If you've completed all steps successfully, you're ready to start using ElderCare Agent!

**Next steps:**
- Customize the user profile in `data/users/margaret_thompson.yaml`
- Modify agent behaviors in `config/agents.yaml`
- Add new tasks in `config/tasks.yaml`
- Build the web UI
- Deploy to Cloud Run

Happy building! 🚀
