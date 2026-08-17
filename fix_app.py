import re

file_path = 'c:/Users/aml/Desktop/RAILwire/RailMind/frontend/src/App.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r"borderRadius: '0px'", "borderRadius: '8px'"),
    (r"backgroundColor: '#090b0e'", "backgroundColor: 'var(--bg-main)'"),
    (r"backgroundColor: '#11141a'", "backgroundColor: 'var(--bg-panel)'"),
    (r"backgroundColor: '#181c24'", "backgroundColor: 'var(--bg-card)'"),
    (r"border: '1px solid #2b3240'", "border: '1px solid var(--border-color)'"),
    (r"borderBottom: '1px solid #2b3240'", "borderBottom: '1px solid var(--border-color)'"),
    (r"borderTop: '1px solid #2b3240'", "borderTop: '1px solid var(--border-color)'"),
    (r"borderRight: '1px solid #2b3240'", "borderRight: '1px solid var(--border-color)'"),
    (r"borderLeft: '1px solid #2b3240'", "borderLeft: '1px solid var(--border-color)'"),
    (r"\[ NO ANOMALIES RECORDED FOR STATUS: \{filter\} \]", "No anomalies recorded for status: {filter}"),
    (r"\[ SYSTEM ERROR // RAILMIND CRASH \]", "System Encountered an Error"),
    (r"\[ Retrieving Sensor Data... \]", "Retrieving Sensor Data..."),
    (r"\[ Retrieving Timetable... \]", "Retrieving Timetable..."),
    (r"\[ Connecting to System Fleet... \]", "Connecting to System Fleet..."),
    (r"\[ PAGE NOT DEPLOYED \]", "Page Not Deployed"),
    (r"\[ AUTHORIZED MILITARY / COGNITIVE AGENTS ONLY • SEC-SESSION 402 \]", "Authorized Personnel Only"),
    (r"\[ ACTIVE // NOMINAL \]", "Active"),
    (r"\[ ACTIVE // LIVE TELEMETRY \]", "Active"),
    (r"\[ ACTIVE // MONGO PERSISTENCE \]", "Active"),
    (r"\[ ACTIVE // TWILIO DISPATCH \]", "Active"),
    (r"\[ OFFLINE // RE-ESTABLISHING AGENT CONNECTION... \]", "Offline / Re-establishing connection..."),
]

for old, new in replacements:
    content = re.sub(old, new, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Replacements done.')
