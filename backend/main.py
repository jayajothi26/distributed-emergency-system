import os
import psycopg2
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------
# FASTAPI INIT
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# REDIS CONFIG
# Works on:
# - Render using REDIS_URL
# - Local using localhost fallback
# -----------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

# -----------------------------
# POSTGRES CONNECTION
# Works on:
# - Render using DATABASE_URL
# - Local using localhost fallback
# -----------------------------
def get_db_conn():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host="localhost",
        database="emergency_response",
        user="postgres",
        password="Jothi@2006"
    )

# -----------------------------
# OPTIONAL: CREATE TABLE IF NOT EXISTS
# -----------------------------
def init_db():
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id SERIAL PRIMARY KEY,
            incident_type VARCHAR(50),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            description TEXT
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# -----------------------------
# STARTUP EVENT
# -----------------------------
@app.on_event("startup")
def startup_event():
    init_db()

# -----------------------------
# WEBSOCKET MANAGER
# -----------------------------
clients = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in clients:
            clients.remove(ws)

# -----------------------------
# BROADCAST FUNCTION
# -----------------------------
async def broadcast_update(data):
    disconnected = []

    for client in clients:
        try:
            await client.send_json(data)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        if client in clients:
            clients.remove(client)

# -----------------------------
# ROOT ROUTE
# -----------------------------
@app.get("/")
async def root():
    return {"message": "Emergency Response API is running"}

# -----------------------------
# REPORT EMERGENCY
# -----------------------------
@app.post("/report_emergency")
async def report_emergency(incident_type: str, lat: float, lon: float, desc: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO incidents (incident_type, latitude, longitude, description)
            VALUES (%s, %s, %s, %s)
            RETURNING incident_id
            """,
            (incident_type, lat, lon, desc)
        )

        incident_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        # Initial status
        r.set(f"incident:{incident_id}:status", "pending")

        await broadcast_update({
            "id": incident_id,
            "status": "pending"
        })

        return {
            "status": "Emergency Reported",
            "incident_id": incident_id
        }

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# CHECK STATUS
# -----------------------------
@app.get("/check_status/{incident_id}")
async def check_status(incident_id: int):
    try:
        status = r.get(f"incident:{incident_id}:status")

        if status:
            return {"incident_id": incident_id, "status": status}

        return {"incident_id": incident_id, "status": "pending"}

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# GET ALL INCIDENTS
# -----------------------------
@app.get("/all_incidents")
async def get_all_incidents():
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT incident_id, incident_type, latitude, longitude
            FROM incidents
            ORDER BY incident_id DESC
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        incidents = []
        for row in rows:
            incidents.append({
                "id": row[0],
                "type": row[1],
                "lat": row[2],
                "lon": row[3]
            })

        return incidents

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# UPDATE STATUS
# -----------------------------
@app.post("/update_status")
async def update_status(incident_id: int, status: str):
    try:
        r.set(f"incident:{incident_id}:status", status)

        await broadcast_update({
            "id": incident_id,
            "status": status
        })

        return {"message": "Status updated"}

    except Exception as e:
        return {"error": str(e)}