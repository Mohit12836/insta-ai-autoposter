from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from instagram_engine import InstagramManager, DB_PATH
from agent import HermesLangGraphAgent
import sqlite3
import os
import shutil
import uvicorn
import uuid

app = FastAPI(title="Buffer-Grade Instagram AI OS")

UPLOAD_DIR = "/opt/insta-ai-autoposter/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

class PageRegisterRequest(BaseModel):
    page_name: str
    ig_user_id: str
    access_token: str

class ContentGenRequest(BaseModel):
    topic: str
    niche: Optional[str] = "business"
    tone: Optional[str] = "viral"

class SchedulePostRequest(BaseModel):
    caption: str
    media_url: str
    media_type: Optional[str] = "IMAGE"
    scheduled_at: Optional[str] = None
    page_ids: Optional[List[int]] = None

@app.get("/api/pages")
def get_pages():
    return {"pages": InstagramManager.list_pages()}

@app.post("/api/pages")
def add_page(req: PageRegisterRequest):
    return InstagramManager.add_page(req.page_name, req.ig_user_id, req.access_token)

@app.delete("/api/pages/{page_id}")
def delete_page(page_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM instagram_pages WHERE id = ?", (page_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Page removed"}

@app.post("/api/generate-ai")
def generate_ai(req: ContentGenRequest):
    return HermesLangGraphAgent.generate_viral_content(req.topic, req.niche, req.tone)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Public URL
    url = f"http://72.61.232.114:8090/uploads/{filename}"
    return {"status": "success", "url": url, "filename": filename}

@app.get("/api/posts")
def get_posts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
    SELECT q.*, p.page_name 
    FROM post_queue q
    LEFT JOIN instagram_pages p ON q.page_id = p.id
    ORDER BY q.created_at DESC LIMIT 50
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"posts": rows}

@app.post("/api/publish")
def publish(req: SchedulePostRequest):
    pages = InstagramManager.list_pages()
    target_ids = req.page_ids if req.page_ids else [p["id"] for p in pages]
    
    results = []
    for pid in target_ids:
        res = InstagramManager.publish_to_page(pid, req.media_url, req.caption, req.media_type)
        results.append({"page_id": pid, "result": res})
        
    return {"status": "completed", "results": results}

@app.post("/n8n-trigger")
def n8n_trigger(req: dict):
    topic = req.get("topic", "Trending AI news")
    niche = req.get("niche", "business")
    media_url = req.get("media_url", "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080")
    media_type = req.get("media_type", "IMAGE")
    
    ai_res = HermesLangGraphAgent.generate_viral_content(topic, niche)
    caption = ai_res["caption"]
    
    results = InstagramManager.publish_to_all_pages(media_url, caption, media_type)
    return {"status": "success", "caption": caption, "results": results}

@app.get("/", response_class=HTMLResponse)
def luxury_buffer_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Vismart Social Studio | Buffer-Grade AI Auto-Poster</title>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
      <style>
        :root {
          --bg-main: #090d16;
          --bg-card: #111726;
          --bg-sidebar: #0b111e;
          --border: #1e293b;
          --accent: #6366f1;
          --accent-hover: #4f46e5;
          --insta-pink: #e1306c;
          --text-main: #f8fafc;
          --text-muted: #94a3b8;
          --success: #10b981;
        }
        * { box-sizing: border-box; margin:0; padding:0; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg-main); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }

        /* Sidebar */
        aside { width: 260px; background: var(--bg-sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 24px 16px; flex-shrink: 0; }
        .logo { font-size: 20px; font-weight: 800; background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 32px; display: flex; align-items: center; gap: 8px; }
        .nav-item { padding: 12px 14px; border-radius: 8px; color: var(--text-muted); font-size: 14px; font-weight: 600; cursor: pointer; transition: 0.2s; margin-bottom: 6px; display: flex; align-items: center; gap: 10px; }
        .nav-item:hover, .nav-item.active { background: #1e293b; color: #fff; }
        .nav-item.active { border-left: 3px solid var(--accent); }

        /* Main Workspace */
        main { flex: 1; display: flex; overflow: hidden; }
        .editor-pane { flex: 1; padding: 32px; overflow-y: auto; max-width: 760px; }
        .preview-pane { width: 440px; background: #0c121f; border-left: 1px solid var(--border); padding: 32px 24px; display: flex; flex-direction: column; align-items: center; overflow-y: auto; flex-shrink: 0; }

        h2 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
        p.subtitle { color: var(--text-muted); font-size: 14px; margin-bottom: 24px; }

        /* Account Picker Bar */
        .account-pills { display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }
        .pill { background: #1a2234; border: 1px solid var(--border); padding: 8px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; cursor: pointer; transition: 0.2s; }
        .pill.selected { background: #252e47; border-color: var(--accent); color: #fff; box-shadow: 0 0 12px rgba(99,102,241,0.3); }
        .pill-badge { width: 10px; height: 10px; border-radius: 50%; background: var(--insta-pink); display: inline-block; }

        /* Card Section */
        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 22px; margin-bottom: 22px; box-shadow: 0 8px 30px rgba(0,0,0,0.2); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        .card-title { font-size: 15px; font-weight: 700; color: #e2e8f0; }

        /* Inputs & Textareas */
        input, textarea, select { width: 100%; background: #0a0f1d; border: 1px solid var(--border); color: #fff; padding: 12px 14px; border-radius: 8px; font-family: inherit; font-size: 14px; transition: 0.2s; margin-bottom: 12px; }
        input:focus, textarea:focus { border-color: var(--accent); outline: none; }
        textarea { resize: vertical; min-height: 120px; line-height: 1.6; }

        /* Buttons */
        .btn-primary { background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; border: none; font-weight: 700; padding: 14px 20px; border-radius: 10px; font-size: 15px; cursor: pointer; transition: 0.2s; width: 100%; box-shadow: 0 4px 14px rgba(99,102,241,0.35); }
        .btn-primary:hover { opacity: 0.95; transform: translateY(-1px); }
        .btn-ai { background: linear-gradient(135deg, #ec4899, #8b5cf6); color: #fff; border: none; font-weight: 700; padding: 10px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }

        /* Phone Mockup (Instagram Simulator) */
        .phone { width: 330px; background: #000; border: 3px solid #2d3748; border-radius: 36px; padding: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative; }
        .notch { width: 120px; height: 18px; background: #2d3748; border-radius: 0 0 12px 12px; margin: -16px auto 14px; }
        .ig-post { background: #000; color: #fff; font-family: -apple-system, sans-serif; font-size: 13px; border-radius: 12px; overflow: hidden; }
        .ig-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; }
        .ig-user { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13px; }
        .ig-avatar { width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); padding: 2px; }
        .ig-avatar-inner { width: 100%; height: 100%; border-radius: 50%; background: #222; }
        .ig-media { width: 100%; aspect-ratio: 1/1; background: #1a202c; border-radius: 6px; object-fit: cover; display: flex; align-items: center; justify-content: center; color: #718096; overflow: hidden; }
        .ig-actions { display: flex; gap: 14px; font-size: 18px; padding: 10px 0 6px; }
        .ig-caption { line-height: 1.4; color: #e2e8f0; max-height: 140px; overflow-y: auto; white-space: pre-wrap; margin-top: 4px; }
        .ig-caption b { font-weight: 600; margin-right: 6px; }

        /* Media Dropzone */
        .dropzone { border: 2px dashed #334155; border-radius: 10px; padding: 20px; text-align: center; cursor: pointer; transition: 0.2s; background: #090f1d; margin-bottom: 14px; }
        .dropzone:hover { border-color: var(--accent); }
      </style>
    </head>
    <body>

      <!-- Sidebar -->
      <aside>
        <div class="logo">⚡ VISMART SOCIAL</div>
        <div class="nav-item active" onclick="showTab('composer')">📝 Composer & Post</div>
        <div class="nav-item" onclick="showTab('accounts')">📱 Connected Pages</div>
        <div class="nav-item" onclick="showTab('queue')">⏳ Scheduled Queue</div>
        <div class="nav-item" onclick="window.open('http://72.61.232.114:5678', '_blank')">⚙️ n8n Automation</div>
        
        <div style="margin-top:auto; font-size:12px; color:#64748b; line-height:1.5;">
          Running on VPS: <b>72.61.232.114</b><br>
          Buffer Engine v2.4 (Active)
        </div>
      </aside>

      <!-- Main Workspace -->
      <main>
        <!-- Editor Pane -->
        <div class="editor-pane" id="composer-tab">
          <h2>Create & Schedule Post</h2>
          <p class="subtitle">Select your Instagram accounts, let Hermes AI craft viral copy, and publish everywhere.</p>

          <!-- Accounts Selection -->
          <label style="font-size:13px; font-weight:700; color:#cbd5e1; margin-bottom:8px; display:block;">Target Accounts:</label>
          <div class="account-pills" id="pills-container">
            <!-- Dynamically populated -->
          </div>

          <!-- AI Generator Box -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">🧠 Hermes AI Content Engine</span>
              <button class="btn-ai" onclick="generateWithAI()">✨ Generate Viral Copy</button>
            </div>
            <input id="ai-topic" placeholder="What is this post about? (e.g. 3 secret AI tools for real estate in 2026)" />
            <div style="display:flex; gap:10px;">
              <select id="ai-niche">
                <option value="business">Business & Scaling</option>
                <option value="real estate">Real Estate</option>
                <option value="digital marketing">Digital Marketing & Ads</option>
                <option value="tech and ai">AI & Automation</option>
              </select>
              <select id="ai-tone">
                <option value="viral">Viral & Punchy</option>
                <option value="educational">Educational & Authority</option>
                <option value="storytelling">Storytelling & Emotional</option>
              </select>
            </div>
          </div>

          <!-- Post Content -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">✍️ Caption & Hashtags</span>
              <span id="char-count" style="font-size:12px; color:#64748b;">0 chars</span>
            </div>
            <textarea id="caption" placeholder="Write your post caption or generate with AI above..." oninput="updatePreview()"></textarea>

            <div class="card-title" style="margin: 16px 0 8px;">🖼️ Media Asset (Image or Reel Video)</div>
            <div class="dropzone" onclick="document.getElementById('file-input').click()">
              <input type="file" id="file-input" style="display:none;" onchange="handleFileUpload(this.files)" accept="image/*,video/*" />
              <div id="drop-text">📁 Click to Upload Media from Computer (or enter URL below)</div>
            </div>
            <input id="media-url" placeholder="Or paste public image/video URL directly..." oninput="updatePreview()" />

            <div style="display:flex; gap:12px; margin-top:8px;">
              <select id="media-type" onchange="updatePreview()">
                <option value="IMAGE">Single Image Post</option>
                <option value="REELS">Instagram Reel (Video)</option>
              </select>
            </div>
          </div>

          <button class="btn-primary" onclick="publishNow()">🚀 Publish Instantly Across Selected Accounts</button>
          <div id="publish-status" style="margin-top:14px; font-size:14px; font-weight:600;"></div>
        </div>

        <!-- Accounts Tab -->
        <div class="editor-pane" id="accounts-tab" style="display:none;">
          <h2>Connect & Manage Instagram Pages</h2>
          <p class="subtitle">Connect your official Meta Instagram Business accounts with zero limit.</p>

          <div class="card">
            <div class="card-title">Add New Instagram Account</div>
            <input id="new-pname" placeholder="Account Display Name (e.g. Agency Main)" />
            <input id="new-pid" placeholder="Instagram Business Account ID (17841400...)" />
            <input id="new-ptoken" placeholder="Page Access Token (EAAB...)" />
            <button class="btn-primary" onclick="addNewAccount()">+ Connect Instagram Account</button>
          </div>

          <div class="card">
            <div class="card-title" style="margin-bottom:14px;">Active Connected Pages</div>
            <div id="connected-list">Loading...</div>
          </div>
        </div>

        <!-- Queue Tab -->
        <div class="editor-pane" id="queue-tab" style="display:none;">
          <h2>Post History & Queue</h2>
          <p class="subtitle">Real-time status of published and scheduled posts.</p>
          <div id="queue-list">Loading...</div>
        </div>

        <!-- Preview Pane (Live Instagram Phone Mockup) -->
        <div class="preview-pane">
          <div style="font-size:13px; font-weight:700; color:#cbd5e1; margin-bottom:14px; text-transform:uppercase; letter-spacing:1px;">Live Instagram Preview</div>
          
          <div class="phone">
            <div class="notch"></div>
            <div class="ig-post">
              <div class="ig-header">
                <div class="ig-user">
                  <div class="ig-avatar"><div class="ig-avatar-inner"></div></div>
                  <span id="preview-user">vismart.ai</span>
                </div>
                <span>•••</span>
              </div>

              <div class="ig-media" id="preview-media-box">
                <img id="preview-img" style="display:none; width:100%; height:100%; object-fit:cover;" />
                <span id="preview-media-placeholder">No Media Selected</span>
              </div>

              <div class="ig-actions">
                <span>❤️</span>
                <span>💬</span>
                <span>✈️</span>
                <span style="margin-left:auto;">🔖</span>
              </div>

              <div style="font-weight:600; font-size:12px; margin-bottom:4px;">1,284 likes</div>
              <div class="ig-caption">
                <b id="preview-caption-user">vismart.ai</b><span id="preview-caption-text">Your caption will appear here in real-time as you type or generate with Hermes AI...</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <script>
        let accounts = [];
        let selectedAccountIds = [];

        async function loadPages() {
          const res = await fetch('/api/pages');
          const data = await res.json();
          accounts = data.pages || [];
          
          // Render Pills
          const container = document.getElementById('pills-container');
          if (accounts.length === 0) {
            container.innerHTML = '<span style="color:#ef4444; font-size:13px;">No Instagram accounts connected yet. Go to Connected Pages tab to add!</span>';
          } else {
            container.innerHTML = accounts.map(a => `
              <div class="pill ${selectedAccountIds.includes(a.id) ? 'selected' : ''}" onclick="toggleAccount(${a.id})">
                <span class="pill-badge"></span>
                <span>${a.page_name}</span>
              </div>
            `).join('');
            if (selectedAccountIds.length === 0 && accounts.length > 0) {
              selectedAccountIds = [accounts[0].id];
              loadPages();
            }
          }

          // Render Accounts List tab
          const list = document.getElementById('connected-list');
          if (list) {
            list.innerHTML = accounts.map(a => `
              <div style="display:flex; justify-content:space-between; align-items:center; padding:12px; background:#090f1d; border-radius:8px; margin-bottom:8px;">
                <div>
                  <div style="font-weight:700;">${a.page_name}</div>
                  <div style="font-size:12px; color:#64748b;">ID: ${a.ig_user_id}</div>
                </div>
                <button onclick="deleteAccount(${a.id})" style="background:#ef4444; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:12px; cursor:pointer;">Remove</button>
              </div>
            `).join('') || '<div style="color:#64748b;">No pages added.</div>';
          }
        }

        function toggleAccount(id) {
          if (selectedAccountIds.includes(id)) {
            selectedAccountIds = selectedAccountIds.filter(x => x !== id);
          } else {
            selectedAccountIds.push(id);
          }
          loadPages();
          updatePreview();
        }

        async function addNewAccount() {
          const name = document.getElementById('new-pname').value;
          const id = document.getElementById('new-pid').value;
          const token = document.getElementById('new-ptoken').value;
          if (!name || !id || !token) return alert('Please fill all fields');
          
          await fetch('/api/pages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({page_name: name, ig_user_id: id, access_token: token})
          });
          alert('Account connected successfully!');
          showTab('composer');
          loadPages();
        }

        async function deleteAccount(id) {
          if (!confirm('Remove this account?')) return;
          await fetch(`/api/pages/${id}`, {method: 'DELETE'});
          loadPages();
        }

        async function generateWithAI() {
          const topic = document.getElementById('ai-topic').value;
          if (!topic) return alert('Please enter a topic first!');
          const btn = document.querySelector('.btn-ai');
          btn.innerText = '⏳ Thinking...';
          
          try {
            const res = await fetch('/api/generate-ai', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                topic: topic,
                niche: document.getElementById('ai-niche').value,
                tone: document.getElementById('ai-tone').value
              })
            });
            const data = await res.json();
            document.getElementById('caption').value = data.caption;
            updatePreview();
          } catch(e) {
            alert('AI error: ' + e);
          } finally {
            btn.innerText = '✨ Generate Viral Copy';
          }
        }

        async function handleFileUpload(files) {
          if (!files || files.length === 0) return;
          const file = files[0];
          document.getElementById('drop-text').innerText = '⏳ Uploading ' + file.name + '...';
          
          const formData = new FormData();
          formData.append('file', file);
          
          const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.status === 'success') {
            document.getElementById('media-url').value = data.url;
            document.getElementById('drop-text').innerText = '✅ Uploaded: ' + file.name;
            updatePreview();
          }
        }

        function updatePreview() {
          const caption = document.getElementById('caption').value;
          const mediaUrl = document.getElementById('media-url').value;
          document.getElementById('preview-caption-text').innerText = caption || 'Your caption will appear here in real-time...';
          document.getElementById('char-count').innerText = `${caption.length} chars`;

          const img = document.getElementById('preview-img');
          const placeholder = document.getElementById('preview-media-placeholder');
          if (mediaUrl) {
            img.src = mediaUrl;
            img.style.display = 'block';
            placeholder.style.display = 'none';
          } else {
            img.style.display = 'none';
            placeholder.style.display = 'block';
          }

          if (selectedAccountIds.length > 0) {
            const acc = accounts.find(a => a.id === selectedAccountIds[0]);
            if (acc) {
              document.getElementById('preview-user').innerText = acc.page_name.toLowerCase().replace(/\\s+/g, '_');
              document.getElementById('preview-caption-user').innerText = acc.page_name.toLowerCase().replace(/\\s+/g, '_');
            }
          }
        }

        async function publishNow() {
          const caption = document.getElementById('caption').value;
          const mediaUrl = document.getElementById('media-url').value;
          if (!caption || !mediaUrl) return alert('Please provide both Caption and Media URL!');
          if (selectedAccountIds.length === 0) return alert('Please select at least 1 Instagram account!');

          const status = document.getElementById('publish-status');
          status.style.color = '#38bdf8';
          status.innerText = '🚀 Publishing to selected accounts...';

          const res = await fetch('/api/publish', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              caption: caption,
              media_url: mediaUrl,
              media_type: document.getElementById('media-type').value,
              page_ids: selectedAccountIds
            })
          });

          const data = await res.json();
          status.style.color = '#10b981';
          status.innerText = '✅ Post Processed! Results: ' + JSON.stringify(data.results);
        }

        function showTab(tab) {
          document.getElementById('composer-tab').style.display = tab === 'composer' ? 'block' : 'none';
          document.getElementById('accounts-tab').style.display = tab === 'accounts' ? 'block' : 'none';
          document.getElementById('queue-tab').style.display = tab === 'queue' ? 'block' : 'none';
          document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
          event.target.classList.add('active');
          if (tab === 'queue') loadQueue();
        }

        async function loadQueue() {
          const res = await fetch('/api/posts');
          const data = await res.json();
          const list = document.getElementById('queue-list');
          list.innerHTML = data.posts.map(p => `
            <div style="background:#0c121f; border:1px solid #1e293b; padding:16px; border-radius:10px; margin-bottom:12px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="font-weight:700; color:#38bdf8;">${p.page_name || 'Account'}</span>
                <span style="background:${p.status === 'PUBLISHED' ? '#10b981' : '#ef4444'}; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px;">${p.status}</span>
              </div>
              <div style="font-size:13px; color:#cbd5e1; white-space:pre-wrap; max-height:60px; overflow:hidden;">${p.caption}</div>
              <div style="font-size:11px; color:#64748b; margin-top:8px;">${p.created_at}</div>
            </div>
          `).join('') || '<div style="color:#64748b;">No post history yet.</div>';
        }

        loadPages();
      </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
