# RailMind

Autonomous multi-agent orchestration system for real-time railway anomaly detection, reasoning, department task dispatching, and live operations management.

## 🏗️ Architecture & Agent Flow

RailMind operates on an autonomous LangGraph pipeline, pulling telemetry, analyzing safety parameters, generating intelligent mitigation plans via Claude, dispatching actions, and broadcasting live updates.

```
                  +--------------------------------+
                  |      Indian Railways API       |
                  +---------------+----------------+
                                  |
                                  v
                  +---------------+----------------+
                  |          Ingest Node           |
                  +---------------+----------------+
                                  |
                                  v
                  +---------------+----------------+
                  |          Detect Node           |
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            | (Anomalies detected?)                     | (No anomalies)
            v Yes                                       v
+-----------+------------+                    +---------+--------+
|      Reason Node       |                    |    End Loop /    |
|  (Claude 3.5 Sonnet)   |                    |   Ingest Node    |
+-----------+------------+                    +------------------+
            |
            v
+-----------+------------+
|      Reroute Node      |
+-----------+------------+
|  Calculates bypass     |
|  routes & detours      |
+-----------+------------+
            |
            v
+-----------+------------+
|   Coordination Agent   |
+-----------+------------+
            |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
+-----------+-----------+ +---------+-----------+ +---------+-----------+
|    Maintenance Task   | |    Operations Task  | | Station Manager Task|
| - Repair dispatch     | | - Rerouting execution| | - Announcements &   |
| - High urgency        | | - Medium/High urgency| |   platform updates  |
+-----------+-----------+ +---------+-----------+ +---------+-----------+
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
                                    v
                        +-----------+-----------+
                        |      Alert Node       | (Twilio SMS triggers)
                        +-----------+-----------+
                                    |
                                    v
                        +-----------+-----------+
                        |      Report Node      | (Resets state & logs loop)
                        +-----------+-----------+
                                    |
                      +-------------+-------------+
                      |                           |
                      v                           v
        +-------------+-------------+ +-----------+-------------+
        |      MongoDB Server       | |    WebSocket Server     |
        |  - Incidents Collection   | |  - Real-time stream     |
        |  - Tasks Collection       | |  - Live operations logs |
        +---------------------------+ +-----------+-------------+
                                                  |
                                                  v
                                      +-----------+-------------+
                                      |     React Dashboard     |
                                      +-------------------------+
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python) | High-performance asynchronous REST and WebSocket API server. |
| **Orchestration** | LangGraph | State-machine graph modeling for reliable multi-agent workflows. |
| **Reasoning Engine** | Claude 3.5 Sonnet (Anthropic) | Multi-parameter decision-making, incident summary compilation, and department task formulation. |
| **Database** | MongoDB | Persistent document storage for live incident reports and department task boards. |
| **Notifications** | Twilio SMS API | Instant notifications to operational heads during critical alerts. |
| **Frontend Framework**| React 19 + Vite | Premium responsive dashboard utilizing dynamic rendering. |
| **Telemetry Map** | React-Leaflet (Leaflet.js) | Dynamic map widget with custom train location markers. |
| **Styling** | Vanilla CSS | Custom theme control, layout aesthetics, and smooth animations. |

---

## ✨ Features

- **Autonomous Telemetry Ingestion**: Seamless ingestion of live Indian Railways trains, locations, and time tables.
- **Safety Parameter Guardians**: Real-time evaluation of speed limits, route adherence, and delay metrics.
- **Cognitive Incident Reasoning**: Employs Claude 3.5 Sonnet to construct incident summaries and dynamically structure corrective tasks.
- **Multi-Department Coordination**: Automatically translates Claude's findings into actionable items across **Maintenance**, **Operations**, and **Station Management** dashboards.
- **Proactive Twilio Alerts**: Instantly triggers SMS notifications to target coordinators for critical speed warnings or severe track delays.
- **Operations Log Console**: Terminal emulator interface streaming state-graph logs and system steps live to the control room.
- **Live Interactive Dashboard**: Responsive controls for approving reroute plans, resolving department tasks, and visualizing maps.

---

## ⚙️ Setup Instructions

### Prerequisites
- **Python 3.11+** installed.
- **Node.js 18+** installed.
- **MongoDB** running locally (port `27017`) or a **MongoDB Atlas** connection string.

### 1. Clone & Configuration
Clone the repository to your machine:
```bash
git clone https://github.com/Shreyam007/RailMind.git
cd RailMind/railmind
```

### 2. Backend Environment Configuration
Create a `.env` file in the `backend/` directory:
```bash
cp backend/.env.example backend/.env
```
Populate the variables in `backend/.env` with your active keys.

### 3. Backend Setup
1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

### 4. Frontend Setup
1. Open a new terminal in the `frontend/` directory.
2. Install npm packages:
   ```bash
   npm install
   ```

---

## 🔑 Environment Variables

Configure these keys inside your `backend/.env` file:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB Connection URL | `mongodb://localhost:27017/railmind` |
| `ANTHROPIC_API_KEY` | Claude Anthropic developer API key | `sk-ant-api03-...` |
| `TWILIO_ACCOUNT_SID` | Twilio Account Identifier | `ACxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio API Authorization token | `your_auth_token_here` |
| `TWILIO_PHONE_NUMBER` | Twilio SMS sender phone number | `+1234567890` |
| `COORDINATOR_PHONE_NUMBER`| SMS notification recipient | `+1987654321` |

---

## 🚀 How to Run

Ensure your MongoDB instance is running, then execute:

### Running the Backend
From the `railmind` root directory (with your virtual environment active):
```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
The API documentation will be available at `http://127.0.0.1:8000/docs`.

### Running the Frontend
From the `railmind/frontend` directory:
```bash
npm run dev
```
Open your browser to `http://localhost:5173/` to view the live dashboard.

---

## 🔗 Live Demo
Access the live deployment: **[TO BE FILLED]**

---

## 👥 Team

> **Team Name:** `nitishrg.8220psgps2020`
> **Institution:** IIT Madras

| # | Name | Role |
| :---: | :--- | :--- |
| 1 | **Nitish R G** 👑 | Team Leader |
| 2 | **Prithic P** | Member |
| 3 | **Shreyam Pandey** | Member |
| 4 | **Padmanabhan SureshBabu** | Member |
| 5 | **Aswin R** | Member |
