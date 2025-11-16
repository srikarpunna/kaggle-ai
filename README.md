# 🏥 ElderCare Agent

**Track:** Agents for Good
**Competition:** Kaggle AI Agents Intensive - Capstone Project

An AI-powered assistant designed to help elderly people manage daily tasks through voice interaction and adaptive, accessible user interfaces.

## 📋 Problem Statement

**67% of seniors struggle with smartphones.** They miss critical medications, feel isolated from family, and can't navigate complex healthcare systems. Apps are too complicated, with tiny buttons, confusing menus, and technical jargon.

## 💡 Solution

ElderCare Agent replaces complex apps with:
- 🗣️ **Voice-first interaction** - Just talk naturally
- 📱 **Adaptive UI** - Task-specific interfaces that appear only when needed
- 🔤 **Large icons & simple language** - Designed for elderly users
- 🧠 **Memory** - Learns relationships and preferences over time
- 🤖 **Multi-agent system** - Specialized agents for different tasks

## ✨ Core Features

### 1. Video Calling Family
- Say "Call my son" → Agent finds John → Shows ONE big button → Call connects
- Supports WhatsApp, FaceTime, regular phone calls
- Remembers family relationships ("my grandson" = Tim)

### 2. Medication Reminders
- Automatic reminders with pill photos and large "I Took It" button
- Tracks adherence
- In-app notifications

### 3. Doctor Appointments
- Book appointments: "I need to see Dr. Smith next Tuesday"
- Syncs with Google Calendar
- Reminders 1 day and 1 hour before

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         USER INTERFACE (Web App)         │
│    Voice Input + Adaptive Simple UI      │
└────────────┬────────────────────────────┘
             │
┌────────────▼───────────────────────────┐
│     ORCHESTRATOR AGENT (Gemini)         │
│  - Understands intent                   │
│  - Routes to specialized agents         │
└──┬──────────┬──────────┬────────────────┘
   │          │          │
   ▼          ▼          ▼
┌─────┐  ┌──────┐  ┌────────┐  ┌────────┐
│COMMS│  │HEALTH│  │UI GEN  │  │MEMORY  │
│AGENT│  │AGENT │  │AGENT   │  │AGENT   │
└──┬──┘  └───┬──┘  └────┬───┘  └───┬────┘
   │         │          │          │
   ▼         ▼          ▼          ▼
┌──────────────────────────────────────┐
│          TOOLS & MCP SERVERS          │
│  - Calendar MCP (Google Calendar)     │
│  - Contacts MCP (SQLite)              │
│  - Health MCP (Medications, SQLite)   │
│  - Speech (Web Speech API)            │
└──────────────────────────────────────┘
```

### Multi-Agent System

1. **Orchestrator Agent** (Gemini 2.0 Flash)
   - Parses voice/text input
   - Classifies intent (call, medication, appointment)
   - Routes to appropriate specialist agent
   - Manages conversation flow

2. **Communication Agent** (Gemini 2.0 Flash)
   - Retrieves contacts from memory
   - Generates deep links (WhatsApp, FaceTime, Phone)
   - Handles relationship mapping ("my son" → John Thompson)

3. **Health Agent** (Gemini 2.0 Flash)
   - Manages medication schedules
   - Sends time-based reminders
   - Books doctor appointments
   - Tracks adherence

4. **UI Generator Agent** (Gemini 2.0 Flash)
   - Selects appropriate UI template
   - Customizes with task-specific data
   - Ensures accessibility (large fonts, high contrast)
   - Removes UI after task completion

5. **Memory Agent** (Gemini 2.0 Flash)
   - Stores user profile and preferences
   - Maintains relationship graph
   - Learns from interactions
   - Provides context to other agents

## 🛠️ Technical Implementation

### Features Demonstrated (Required 3+)

✅ **1. Multi-agent system**
- 5 specialized agents (Orchestrator, Communication, Health, UI Generator, Memory)
- Sequential workflow (Orchestrator → Specialist → UI Generator)
- Parallel execution (Memory + Health agents)

✅ **2. Tools - MCP**
- Contacts MCP Server (SQLite)
- Health MCP Server (Medications, SQLite)
- Calendar MCP Server (Google Calendar API)

✅ **3. Tools - Custom**
- Deep link generator (WhatsApp, FaceTime, Phone)
- Speech-to-text (Web Speech API)
- Text-to-speech (Web Speech API)

✅ **4. Sessions & Memory**
- Session management with state persistence
- Memory Bank (SQLite) for long-term learning
- User profiles (YAML)
- Relationship mapping

✅ **5. Observability**
- Structured logging (JSON format)
- Agent call tracing
- Task completion metrics
- Error tracking

✅ **6. Agent Evaluation**
- Automated test suite with 20+ scenarios
- Success metrics (completion rate, accuracy)
- Accessibility validation

### Tech Stack (100% FREE)

| Component | Technology |
|-----------|-----------|
| LLM | Gemini 2.0 Flash (FREE: 15 RPM, 1M tokens/min) |
| Speech-to-Text | Web Speech API (Browser, FREE) |
| Text-to-Speech | Web Speech API (Browser, FREE) |
| Video Calls | Deep links (WhatsApp/FaceTime/Phone, FREE) |
| Calendar | Google Calendar API (FREE: 1M requests/day) |
| Database | SQLite (FREE, serverless) |
| Memory | JSON + SQLite (FREE) |
| Deployment | Google Cloud Run (FREE tier: 2M requests/month) |
| MCP Runtime | Open source (FREE) |

**No paid APIs. No mocking. All real.**

## 🚀 Setup Instructions

### Prerequisites

1. Python 3.10+
2. Google AI Studio API key (FREE)
3. Google Cloud account for Calendar API (FREE)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/eldercare-agent.git
cd eldercare-agent

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Configuration

1. **Get Gemini API Key (FREE)**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Click "Create API Key"
   - Copy key to `.env` file

2. **Set up Google Calendar API (FREE)**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials
   - Download `credentials.json` to `config/` folder

3. **Initialize Databases**
   ```bash
   python src/core/database.py
   ```
   This creates SQLite databases and seeds demo data for Margaret Thompson.

### Running the Application

```bash
# Option 1: Run locally
python src/main.py

# Option 2: Run with Docker
docker-compose up

# Option 3: Deploy to Cloud Run
gcloud run deploy eldercare-agent --source .
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Test individual components
python src/agents/orchestrator.py
python src/core/config_loader.py
python src/core/database.py
```

## 📊 Demo User: Margaret Thompson

The system comes pre-configured with a demo user profile:

- **Name:** Margaret Thompson, 72 years old
- **Family:**
  - Son: John Thompson (WhatsApp video calls)
  - Daughter: Sarah Chen (FaceTime)
  - Grandson: Tim Chen (FaceTime)
- **Medications:**
  - Lisinopril 10mg (9:00 AM daily)
  - Aspirin 81mg (9:00 AM daily)
  - Vitamin D3 2000 IU (12:00 PM daily)
- **Doctor:** Dr. James Smith at City Health Clinic

## 🎯 Example Interactions

### Video Call

```
User: "Call my son"
Agent: [Shows UI with John's photo and large "📞 Video Call" button]
User: [Taps button]
Agent: [Opens WhatsApp video call to John]
       [UI disappears]
```

### Medication Reminder

```
[9:00 AM - Automatic]
Agent: [Shows pill photo]
       "Time for your Lisinopril 10mg for your heart"
       [Large "✓ I Took It" button]
User: [Taps button]
Agent: "Great! Logged."
       [UI disappears]
```

### Doctor Appointment

```
User: "I need to see Dr. Smith next Tuesday"
Agent: "Dr. Smith has these times available:
        - Tuesday 10:30 AM
        - Tuesday 2:00 PM
        Which works better?"
User: "Morning"
Agent: [Shows confirmation UI]
       "✓ Appointment booked for Tuesday 10:30 AM
        I'll remind you 1 day and 1 hour before"
       [Creates Google Calendar event]
```

## 📁 Project Structure

```
eldercare-agent/
├── config/                    # All YAML configurations
│   ├── agents.yaml           # Agent definitions
│   ├── tasks.yaml            # Task workflows
│   ├── prompts.yaml          # LLM prompts
│   ├── ui_templates.yaml     # UI configurations
│   └── mcp_servers.yaml      # MCP server configs
├── data/                      # Databases and user data
│   ├── users/                # User profiles (YAML)
│   │   └── margaret_thompson.yaml
│   ├── contacts.db           # SQLite contacts
│   ├── health.db             # SQLite medications
│   ├── calendar.db           # SQLite appointments
│   └── memory_bank.db        # SQLite memory
├── src/
│   ├── agents/               # All 5 agents
│   │   ├── orchestrator.py
│   │   ├── communication.py
│   │   ├── health.py
│   │   ├── ui_generator.py
│   │   └── memory.py
│   ├── mcp/                  # MCP servers
│   │   ├── calendar_server.py
│   │   ├── contacts_server.py
│   │   └── health_server.py
│   ├── tools/                # Custom tools
│   │   ├── speech.py
│   │   └── deeplink.py
│   ├── ui/                   # Web interface
│   │   └── templates/
│   ├── core/                 # Core utilities
│   │   ├── config_loader.py
│   │   ├── database.py
│   │   └── session_manager.py
│   └── main.py               # Application entry point
├── tests/                     # Test suite
├── docs/                      # Documentation
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔧 Configuration-Driven Architecture

**Everything is configurable via YAML.** No hardcoded values.

- Add new agents → Edit `config/agents.yaml`
- Add new tasks → Edit `config/tasks.yaml`
- Modify prompts → Edit `config/prompts.yaml`
- Change UI → Edit `config/ui_templates.yaml`
- Configure MCP → Edit `config/mcp_servers.yaml`

## 📈 Evaluation Metrics

### Task Success Rates

| Task | Target | Actual |
|------|--------|--------|
| Video Call | 95% | TBD |
| Medication Reminder | 99% | TBD |
| Appointment Booking | 90% | TBD |

### Accessibility Compliance

- ✅ Font size ≥ 24px
- ✅ Button size ≥ 80px × 80px
- ✅ High contrast colors (4.5:1 ratio)
- ✅ Simple language (no jargon)
- ✅ Clear icons with labels

## 🎥 Demo Video

[Link to 3-minute demo video] (To be added)

## 🏆 Why This Wins

1. **Massive Real-World Impact**
   - Helps millions of elderly people
   - Addresses critical accessibility gap
   - Proven need (67% of seniors struggle with apps)

2. **Technical Excellence**
   - 5-agent multi-agent system
   - 3 MCP servers + custom tools
   - Full memory & session management
   - Comprehensive observability
   - Automated evaluation

3. **100% Real Implementation**
   - No mocking or simulation
   - Real Gemini API integration
   - Real Google Calendar integration
   - Real SQLite databases
   - All FREE technologies

4. **Accessibility-First Design**
   - Large fonts, high contrast
   - Voice-first interaction
   - Simple, adaptive UI
   - Tested for elderly users

5. **Config-Driven Architecture**
   - Clean, maintainable code
   - Easy to extend
   - Well-documented
   - Production-ready

## 🚧 Future Enhancements

- [ ] Add more family members
- [ ] Integrate with pharmacy for automatic refills
- [ ] Add emergency contact quick dial
- [ ] Support multiple languages
- [ ] Add health vitals tracking (blood pressure, etc.)
- [ ] Integration with smart home devices

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Google & Kaggle for the AI Agents Intensive Course
- Gemini API for powerful, free LLM access
- Open source MCP community

## 📧 Contact

[Your Name]
[Your Email]
[Your GitHub]

---

**Built with ❤️ to help elderly people stay connected, healthy, and independent.**
