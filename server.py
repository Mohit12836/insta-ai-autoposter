from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from instagram_engine import InstagramManager
from agent import HermesLangGraphAgent
import uvicorn

app = FastAPI(title="Multi-Page Instagram Auto-Poster & AI Hub")

class PageRegisterRequest(BaseModel):
    page_name: str
    ig_user_id: str
    access_token: str

class ContentGenRequest(BaseModel):
    topic: str
    niche: Optional[str] = "business"
    tone: Optional[str] = "viral"

class PublishRequest(BaseModel):
    media_url: str
    caption: str
    media_type: Optional[str] = "IMAGE"
    page_ids: Optional[List[int]] = None # None means all pages

class N8NTriggerRequest(BaseModel):
    topic: str
    media_url: str
    niche: Optional[str] = "business"
    media_type: Optional[str] = "IMAGE"
    page_ids: Optional[List[int]] = None

@app.get("/pages")
def get_pages():
    return {"pages": InstagramManager.list_pages()}

@app.post("/pages")
def add_page(req: PageRegisterRequest):
    return InstagramManager.add_page(req.page_name, req.ig_user_id, req.access_token)

@app.post("/generate-content")
def generate_content(req: ContentGenRequest):
    return HermesLangGraphAgent.generate_viral_content(req.topic, req.niche, req.tone)

@app.post("/publish")
def publish(req: PublishRequest):
    if req.page_ids:
        results = []
        for pid in req.page_ids:
            res = InstagramManager.publish_to_page(pid, req.media_url, req.caption, req.media_type)
            results.append({"page_id": pid, "result": res})
        return {"status": "completed", "results": results}
    else:
        return {"status": "completed", "results": InstagramManager.publish_to_all_pages(req.media_url, req.caption, req.media_type)}

@app.post("/n8n-trigger")
def n8n_unified_trigger(req: N8NTriggerRequest):
    """
    Unified Endpoint for n8n:
    1. Generates viral caption via Hermes AI
    2. Publishes to all connected Instagram pages
    """
    ai_res = HermesLangGraphAgent.generate_viral_content(req.topic, req.niche)
    caption = ai_res["caption"]
    
    if req.page_ids:
        results = [InstagramManager.publish_to_page(pid, req.media_url, caption, req.media_type) for pid in req.page_ids]
    else:
        results = InstagramManager.publish_to_all_pages(req.media_url, caption, req.media_type)
        
    return {
        "status": "success",
        "generated_caption": caption,
        "results": results
    }

@app.get("/", response_class=HTMLResponse)
def dashboard():
    pages = InstagramManager.list_pages()
    pages_html = "".join([
        f"<li style='padding:8px 0; border-bottom:1px solid #334155;'><b>{p['page_name']}</b> (ID: {p['ig_user_id']})</li>"
        for p in pages
    ]) or "<li style='color:#94a3b8;'>No pages connected yet. Add one below!</li>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Instagram Multi-Page AI Publisher</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin:0; padding:40px; }}
        .card {{ background: #1e293b; padding: 24px; border-radius: 12px; max-width: 650px; margin: 0 auto 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
        h1, h2 {{ color: #38bdf8; margin-top:0; }}
        input, textarea, button {{ width: 100%; box-sizing: border-box; padding: 12px; margin: 8px 0; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #fff; }}
        button {{ background: #0284c7; color: white; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }}
        button:hover {{ background: #0369a1; }}
        ul {{ list-style: none; padding: 0; }}
        .badge {{ background: #059669; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>🚀 Instagram Multi-Page AI Publisher</h1>
        <p>Connected directly to <b>n8n</b> & <b>Hermes AI Agent</b>.</p>
        <span class="badge">API Status: Online (Port 8000)</span>
      </div>

      <div class="card">
        <h2>📱 Connected Instagram Pages</h2>
        <ul>{pages_html}</ul>
        
        <h3 style="margin-top:20px; font-size:15px; color:#cbd5e1;">Add New Instagram Page:</h3>
        <input id="pname" placeholder="Page Name (e.g. My Agency Main)" />
        <input id="pid" placeholder="Instagram Business Account ID (e.g. 17841400...)" />
        <input id="ptoken" placeholder="Page Access Token (EAAB...)" />
        <button onclick="addPage()">Connect Page</button>
      </div>

      <div class="card">
        <h2>⚡ Instant 1-Click Multi-Page Post</h2>
        <input id="topic" placeholder="Topic (e.g. 5 AI tools for business in 2026)" />
        <input id="murl" placeholder="Public Image / Reel Video URL (e.g. https://.../image.jpg)" />
        <button onclick="publishPost()">Generate with Hermes AI & Publish Everywhere</button>
        <p id="res-box" style="margin-top:12px; color:#38bdf8; font-size:14px; white-space:pre-wrap;"></p>
      </div>

      <script>
        async function addPage() {{
          const res = await fetch('/pages', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
              page_name: document.getElementById('pname').value,
              ig_user_id: document.getElementById('pid').value,
              access_token: document.getElementById('ptoken').value
            }})
          }});
          const data = await res.json();
          alert(data.message || 'Page added!');
          location.reload();
        }}

        async function publishPost() {{
          const resBox = document.getElementById('res-box');
          resBox.innerText = '⏳ Hermes AI is writing viral caption & publishing...';
          const res = await fetch('/n8n-trigger', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
              topic: document.getElementById('topic').value,
              media_url: document.getElementById('murl').value,
              niche: 'business'
            }})
          }});
          const data = await res.json();
          resBox.innerText = JSON.stringify(data, null, 2);
        }}
      </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
