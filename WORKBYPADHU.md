# WORK BY PADHU — RailMind

## What is RailMind?

RailMind is a smart AI system that watches over Indian Railway trains in real time. It can:
- Track where trains are right now
- Spot problems like delays, signal failures, bad weather, or overcrowding
- Think through what to do about those problems using AI
- Find alternate routes when a track is blocked
- Send text messages to the right people (maintenance crew, station managers, etc.)
- Save everything that happens into a database for records

Think of it like a smart control room assistant that never sleeps.

---

## What I Built & How It Works

### 1. Getting Train Data & Spotting Problems

**Files:** `backend/agents/nodes.py`, `backend/services/railways_api.py`

The system pulls live train data every 15 seconds. It checks for:
- **Big Delays** — If a train is more than 30 minutes late, it flags it
- **Signal Failures** — Broken signals or relay issues
- **Bad Weather** — Dense fog (visibility below 50 meters)
- **Track Blockages** — Landslides or physical obstructions on the line
- **Too Many Passengers** — When a train is over 180% full

If any real data is missing or broken, the system fills in safe defaults instead of crashing.

### 2. AI Agents Working Together

**Files:** `backend/agents/graph.py`, `backend/agents/nodes.py`

RailMind uses multiple AI "agents" that work in a chain, one after another:

1. **Ingest** — Pulls in the train data
2. **Detect** — Checks the data for problems
3. **Supervisor** — Reviews everything and catches mistakes (like suggesting a route through a station that's under maintenance)
4. **Reason** — Uses Gemini or Claude AI to think through what action to take
5. **Reroute** — Calculates an alternate path if needed
6. **Coordinate** — Creates tasks for the right departments
7. **Alert** — Sends SMS notifications
8. **Report** — Saves the final incident report

If the Supervisor finds a bad plan, it throws it out and makes the AI try again automatically. If an AI call fails (API down, rate limited), the system handles it gracefully and uses a backup.

### 3. Route Finding Across India

**File:** `backend/agents/routing.py`

I built a map of India's major railway junctions as a graph (stations = points, tracks = connections). This covers:

- **North:** New Delhi, Kanpur, Lucknow, Amritsar, Ambala, etc.
- **East:** Varanasi, Patna, Howrah (Kolkata), Dhanbad, etc.
- **Central & West:** Bhopal, Nagpur, Mumbai, Ahmedabad, Surat, etc.
- **South:** Chennai, Bengaluru, Hyderabad, Pune, Thiruvananthapuram, etc.

When a station is blocked, the system uses Dijkstra's algorithm (a shortest-path method) to find the fastest detour around it.

### 4. Database & Live Updates

**Files:** `backend/services/db_client.py`, `backend/api/main.py`

- **MongoDB** stores all incidents, tasks, and train data in the cloud
- If MongoDB is down, the system automatically saves to a local JSON file as backup
- **WebSocket** sends live updates to the browser dashboard instantly — no need to refresh the page

### 5. SMS Alerts

**File:** `backend/services/twilio_service.py`

When something goes wrong, RailMind sends text messages via Twilio to:
- Maintenance teams
- Operations controllers
- Station managers

There's a demo mode (`DEMO_MODE=true`) so you can test everything without actually sending real texts or spending money.

---

## Testing

The project has proper tests to make sure everything works:
- `test_recovery.py` — Checks that the Supervisor catches bad plans and recovers from errors
- `test_graph.py` — Checks that all the AI agents run in the right order
- `test_all.py` — Checks database connections, AI setup, API calls, and WebSocket broadcasting

---

## How to Run It

### Step 1: Set Up Environment Variables

Create a file called `backend/.env` and put your keys in it:

```env
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/railmind
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
DEMO_MODE=true
```

### Step 2: Start the Backend Server

```powershell
# From the project root folder
uvicorn backend.api.main:app --reload --port 8000
```

### Step 3: Start the Frontend

```powershell
cd frontend
npm run dev
```

Open your browser and go to `http://localhost:5173` to see the dashboard.
