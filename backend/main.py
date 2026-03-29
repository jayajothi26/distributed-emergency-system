import psycopg2
import json
import redis
import os
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
# REDIS (FROM ENV)
# -----------------------------
r = redis.Redis.from_url(
    os.environ.get("REDIS_URL"),
    decode_responses=True
)

# -----------------------------
# POSTGRES CONNECTION (FROM ENV)
# -----------------------------
def get_db_conn():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# -----------------------------
# 🌐 WEBSOCKET MANAGER
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
        clients.remove(ws)

# -----------------------------
# 📡 BROADCAST FUNCTION
# -----------------------------
async def broadcast_update(data):
    disconnected = []

    for client in clients:
        try:
            await client.send_json(data)
        except:
            disconnected.append(client)

    for d in disconnected:
        clients.remove(d)

# -----------------------------
# ROUTES
# -----------------------------
@app.get("/")
async def root():
    return {"message": "Emergency Response API is running"}

# -----------------------------
# 🚨 REPORT EMERGENCY
# -----------------------------
@app.post("/report_emergency")
async def report_emergency(incident_type: str, lat: float, lon: float, desc: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO incidents (incident_type, latitude, longitude, description) VALUES (%s, %s, %s, %s) RETURNING incident_id",
            (incident_type, lat, lon, desc)
        )

        incident_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        # 🔥 SIMULATE PROCESSING (instead of RabbitMQ)
        r.set(f"incident:{incident_id}:status", "pending")

        # Broadcast initial status
        await broadcast_update({
            "id": incident_id,
            "status": "pending"
        })

        return {"status": "Emergency Reported", "incident_id": incident_id}

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# 📊 CHECK STATUS
# -----------------------------
@app.get("/check_status/{incident_id}")
async def check_status(incident_id: int):
    status = r.get(f"incident:{incident_id}:status")

    if status:
        return {"incident_id": incident_id, "status": status}

    return {"status": "pending"}

# -----------------------------
# 🆕 GET ALL INCIDENTS
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
# 🔥 UPDATE STATUS (MANUAL / SIMULATION)
# -----------------------------
@app.post("/update_status")
async def update_status(incident_id: int, status: str):

    r.set(f"incident:{incident_id}:status", status)

    await broadcast_update({
        "id": incident_id,
        "status": status
    })

    return {"message": "Status updated"}