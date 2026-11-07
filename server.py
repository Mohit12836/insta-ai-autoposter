import os
import json
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="VisMart Publish OS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vismart_publish.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/", response_class=HTMLResponse)
def index():
    path = os.path.join(BASE_DIR, "exact_mockup.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VisMart Publish OS Running</h1>"

@app.get("/exact", response_class=HTMLResponse)
def exact_view():
    path = os.path.join(BASE_DIR, "exact_mockup.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/queue")
def get_queue():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
    SELECT q.*, b.name as brand_name, b.niche as brand_niche, b.avatar_initials
    FROM publishing_queue q
    LEFT JOIN brands b ON q.brand_id = b.id
    ORDER BY q.id ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "queue": rows}

@app.get("/api/stats")
def get_stats():
    return {
        "total_brands": 100,
        "connected_accounts": 286,
        "ig_accounts": 96,
        "fb_accounts": 95,
        "yt_channels": 95,
        "today_posts": 48,
        "scheduled_posts": 320,
        "successful_posts": 45,
        "failed_posts": 3,
        "success_rate": "93.7%"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
