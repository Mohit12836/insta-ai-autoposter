import os
import json
import sqlite3
import requests
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "insta_hub.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Connected Instagram Pages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS instagram_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_name TEXT NOT NULL,
        ig_user_id TEXT NOT NULL UNIQUE,
        access_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Post History & Queue Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS post_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER,
        caption TEXT,
        media_url TEXT NOT NULL,
        media_type TEXT DEFAULT 'IMAGE', -- IMAGE, REELS, CAROUSEL
        status TEXT DEFAULT 'PENDING',  -- PENDING, PUBLISHED, FAILED
        creation_id TEXT,
        post_id TEXT,
        error_log TEXT,
        scheduled_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (page_id) REFERENCES instagram_pages(id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

class InstagramManager:
    @staticmethod
    def add_page(page_name: str, ig_user_id: str, access_token: str) -> Dict:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO instagram_pages (page_name, ig_user_id, access_token)
            VALUES (?, ?, ?)
            ON CONFLICT(ig_user_id) DO UPDATE SET
                page_name=excluded.page_name,
                access_token=excluded.access_token
            """, (page_name, ig_user_id, access_token))
            conn.commit()
            return {"status": "success", "message": f"Page '{page_name}' registered successfully!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    @staticmethod
    def list_pages() -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, page_name, ig_user_id, created_at FROM instagram_pages")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def publish_to_page(page_id: int, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict:
        """
        Official 2-Step Meta Instagram Content Publishing Flow
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM instagram_pages WHERE id = ?", (page_id,))
        page = cursor.fetchone()
        
        if not page:
            conn.close()
            return {"status": "error", "message": f"Page ID {page_id} not found"}

        ig_user_id = page["ig_user_id"]
        token = page["access_token"]
        
        # Step 1: Create Media Container
        container_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media"
        params = {
            "caption": caption,
            "access_token": token
        }
        
        if media_type.upper() == "REELS":
            params["video_url"] = media_url
            params["media_type"] = "REELS"
        else:
            params["image_url"] = media_url

        try:
            r1 = requests.post(container_url, data=params, timeout=30)
            res1 = r1.json()
            
            if "id" not in res1:
                error_msg = res1.get("error", {}).get("message", "Container creation failed")
                cursor.execute("""
                INSERT INTO post_queue (page_id, caption, media_url, media_type, status, error_log)
                VALUES (?, ?, ?, ?, 'FAILED', ?)
                """, (page_id, caption, media_url, media_type, error_msg))
                conn.commit()
                conn.close()
                return {"status": "error", "error": error_msg}

            creation_id = res1["id"]

            # Step 2: Publish the Container
            publish_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish"
            pub_params = {
                "creation_id": creation_id,
                "access_token": token
            }
            
            r2 = requests.post(publish_url, data=pub_params, timeout=30)
            res2 = r2.json()

            if "id" in res2:
                post_id = res2["id"]
                cursor.execute("""
                INSERT INTO post_queue (page_id, caption, media_url, media_type, status, creation_id, post_id)
                VALUES (?, ?, ?, ?, 'PUBLISHED', ?, ?)
                """, (page_id, caption, media_url, media_type, creation_id, post_id))
                conn.commit()
                conn.close()
                return {"status": "success", "post_id": post_id, "page_name": page["page_name"]}
            else:
                error_msg = res2.get("error", {}).get("message", "Publish failed")
                cursor.execute("""
                INSERT INTO post_queue (page_id, caption, media_url, media_type, status, creation_id, error_log)
                VALUES (?, ?, ?, ?, 'FAILED', ?, ?)
                """, (page_id, caption, media_url, media_type, creation_id, error_msg))
                conn.commit()
                conn.close()
                return {"status": "error", "error": error_msg}

        except Exception as e:
            conn.close()
            return {"status": "error", "message": str(e)}

    @staticmethod
    def publish_to_all_pages(media_url: str, caption: str, media_type: str = "IMAGE") -> List[Dict]:
        pages = InstagramManager.list_pages()
        results = []
        for p in pages:
            res = InstagramManager.publish_to_page(p["id"], media_url, caption, media_type)
            results.append({"page_id": p["id"], "page_name": p["page_name"], "result": res})
        return results
