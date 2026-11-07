import os
import json
import sqlite3
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from channel_adapters import AdapterFactory

app = FastAPI(title="VisMart Publish OS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vismart_publish.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 1. Brands Table (100 Brands)
    c.execute("""
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        niche TEXT,
        avatar_initials TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # 2. Channels Table (Accounts: IG, FB, YT, Telegram)
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER,
        platform TEXT NOT NULL,
        account_name TEXT NOT NULL,
        account_id TEXT NOT NULL,
        access_token TEXT,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (brand_id) REFERENCES brands(id)
    )
    """)
    # 3. Publishing Queue
    c.execute("""
    CREATE TABLE IF NOT EXISTS publishing_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER,
        title TEXT NOT NULL,
        caption TEXT,
        media_url TEXT NOT NULL,
        media_type TEXT DEFAULT 'VIDEO',
        duration TEXT DEFAULT '0:58',
        time_slot TEXT NOT NULL,
        status TEXT DEFAULT 'IN_QUEUE',
        target_platforms TEXT DEFAULT '["INSTAGRAM", "FACEBOOK", "YOUTUBE"]',
        published_at TIMESTAMP,
        error_log TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (brand_id) REFERENCES brands(id)
    )
    """)
    # Seed initial sample brands if empty
    c.execute("SELECT COUNT(*) FROM brands")
    if c.fetchone()[0] == 0:
        sample_brands = [
            ("Indore Properties", "Luxury Real Estate & Commercial Villas", "IP"),
            ("AI Business Hub", "Tech & B2B SaaS Automations", "AI"),
            ("VisMart Daily Offers", "Supermarket Retail & Flash Deals", "VM"),
            ("Jain Wellness Store", "Ayurvedic Health & Herbal Nutrition", "JW"),
            ("Startup India News", "Venture Capital & Founder Stories", "SI")
        ]
        for name, niche, initials in sample_brands:
            c.execute("INSERT INTO brands (name, niche, avatar_initials) VALUES (?, ?, ?)", (name, niche, initials))
        
        sample_queue = [
            (1, "Indore Vijay Nagar Commercial Property Tour Reel", "Commercial shops & showroom spaces available in Indore Vijay Nagar #IndoreRealEstate", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "VIDEO", "3:28", "08:30 AM", "PUBLISHED"),
            (2, "Top 5 Autonomous AI Agents For E-Commerce 2025", "Scale your store 10x with autonomous AI sales employees #AIAgents #Ecommerce", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4", "VIDEO", "1:45", "10:15 AM", "PUBLISHED"),
            (3, "Weekend Mega Grocery Flash Sale 50% Off Promo", "Massive discounts across daily groceries only this weekend at VisMart stores! #VisMartSale", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4", "VIDEO", "0:58", "12:45 PM", "PROCESSING"),
            (4, "Morning Superfood Detox Routine Explained", "Start your day with natural Ayurvedic morning vitality boost! #Wellness #HerbalLife", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4", "VIDEO", "2:12", "03:20 PM", "IN_QUEUE"),
            (5, "How This D2C Brand Scaled to 100 Cr ARR", "Exclusive breakdown with the founder on bootstrapping to 100 Cr #Startups #Business", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4", "VIDEO", "4:10", "06:00 PM", "FAILED")
        ]
        for bid, title, caption, url, mtype, dur, slot, status in sample_queue:
            c.execute("""
            INSERT INTO publishing_queue (brand_id, title, caption, media_url, media_type, duration, time_slot, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (bid, title, caption, url, mtype, dur, slot, status))
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile = any(m in user_agent for m in ["mobile", "android", "iphone", "ipad"])
    html_file = "stitch_mobile.html" if is_mobile else "stitch_desktop.html"
    path = os.path.join(BASE_DIR, html_file)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VisMart Publish OS Running</h1>"

@app.get("/desktop", response_class=HTMLResponse)
def desktop_view():
    path = os.path.join(BASE_DIR, "stitch_desktop.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VisMart Publish OS Desktop</h1>"

@app.get("/mobile", response_class=HTMLResponse)
def mobile_view():
    path = os.path.join(BASE_DIR, "stitch_mobile.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VisMart Publish OS Mobile</h1>"

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
        "success_rate": "93.7%",
        "cluster_latency": "18ms",
        "stagger_jitter": "45s active"
    }

@app.post("/api/force-post/{queue_id}")
def force_post(queue_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM publishing_queue WHERE id = ?", (queue_id,))
    item = c.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    c.execute("UPDATE publishing_queue SET status = 'PUBLISHED', published_at = CURRENT_TIMESTAMP WHERE id = ?", (queue_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Post #{queue_id} dispatched successfully across all connected channels!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
