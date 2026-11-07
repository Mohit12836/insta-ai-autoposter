import os
import google.genai as genai
from PIL import Image

env_path = os.path.expanduser('~/.gemini/antigravity/free_ai_gateway/.env')
gemini_key = None
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                gemini_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                break

if not gemini_key:
    print('GEMINI_API_KEY not found')
    exit(1)

client = genai.Client(api_key=gemini_key)
im = Image.open('C:/Users/hp/.gemini/antigravity/brain/2e1a6ad4-3a48-40ba-ad07-a0a7986a3abe/.user_uploaded/media_1794067419538_4b0f212c.jpg')

prompt = """
Examine this dashboard mockup image in extreme microscopic detail.
I need to recreate it as a 1:1 pixel-perfect webpage matching colors, layout, and texts.

Please provide:
1. OVERALL THEME & COLORS:
   - Sidebar background: Hex code (deep royal indigo/navy blue?)
   - Header background: Hex code (light grey/white or dark?)
   - Main content background: Hex code (light lavender/grey #F0F2F9 or similar?)
   - Metric cards: Background color, text colors, icon colors, border radius
   - Primary buttons: Exact colors (e.g. green Start, red Pause, purple Force Post)

2. LEFT SIDEBAR:
   - Logo / Title text and icon at the top
   - Exact list of all menu items (icons, labels, active item, any badges)
   - Bottom section/card (Pro plan, upgrade, storage or user)

3. TOP HEADER / NAV:
   - Left side: Title, breadcrumbs or search bar
   - Right side: Notifications, profile name, avatar, status pills

4. TOP METRICS ROW:
   - How many cards? List each card with:
     * Card title
     * Value/number
     * Subtitle / percentage / change indicator
     * Icon & color

5. MIDDLE SECTION:
   - Left: Chart/graph details (type, title, legend, colors)
   - Right: Quick Actions panel & Integrations status (exact buttons, colors, items)

6. LOWER SECTION:
   - Table Title & filter tabs
   - Table columns
   - Each row details (Brand name, slot time, video title & duration thumbnail, platform icons, status badge color & text, action buttons)

7. RIGHT SIDE (if any):
   - Live activity feed / logs list

Format your response clearly.
"""

res = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[im, prompt]
)

with open('d:/whatsapp waba/insta_autopost_hub/image_analysis.txt', 'w', encoding='utf-8') as out:
    out.write(res.text)

print('Success! Analysis length:', len(res.text))
