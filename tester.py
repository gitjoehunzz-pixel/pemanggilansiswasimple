"""
🧪 Stress Test Tool - Pemanggilan Siswa SD Priangan Istiqamah
============================================================
Test offline via WebSocket. Jalankan script ini, lalu buka index.html di browser.

Cara pakai:
  1. python tester.py              # jalankan server + interactive mode
  2. Buka index.html di browser    # auto-connect ke ws://localhost:8765
  3. Ketik perintah di terminal   # atau buka http://localhost:8765/test

Perintah:
  call <nama>         - Panggil 1 siswa
  bulk <n>            - Panggil n siswa random bersamaan
  rapid <n> [delay]   - Panggil n siswa beruntun (default 100ms)
  list                - Tampilkan daftar siswa
  clear               - Reset semua
  stress              - Jalankan stress test lengkap
  quit                - Keluar
"""

import asyncio
import json
import random
import sys
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import websockets

# ==================== CONFIG ====================
PORT_WS = 8765
PORT_HTTP = 8766
SCRIPT_DIR = Path(__file__).parent

# ==================== LOAD STUDENTS ====================
def load_students():
    siswa_file = SCRIPT_DIR / "siswa.txt"
    students = []
    if siswa_file.exists():
        with open(siswa_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Format: "Nama Siswa" or "Nama Siswa | Kelas" or "Nama Siswa | Kelas | Kode"
                parts = [p.strip() for p in line.split("|")]
                name = parts[0]
                cls = parts[1] if len(parts) > 1 else "?"
                code = parts[2] if len(parts) > 2 else cls.lower().replace(" ", "")
                students.append({"name": name, "cls": cls, "code": code})
    else:
        # Fallback sample data
        students = [
            {"name": "Abimana Praga Aksara", "cls": "1 A", "code": "1a"},
            {"name": "Abinaya Keano Parasyad", "cls": "1 A", "code": "1a"},
            {"name": "Ahmad Haidar Ali Darmawan", "cls": "1 A", "code": "1a"},
            {"name": "Aiyra Al Lathiif", "cls": "1 A", "code": "1a"},
            {"name": "Alira Attahiyya Albiruni", "cls": "1 A", "code": "1a"},
            {"name": "Almeer Tsabtaqi Haaziq", "cls": "1 A", "code": "1a"},
            {"name": "Akleema Meysharuna Kinara", "cls": "1 B", "code": "1b"},
            {"name": "Aldebaran Maliq Pramudya", "cls": "1 B", "code": "1b"},
            {"name": "Abyan Hadiyan Alghifari", "cls": "2 A", "code": "2a"},
            {"name": "Adzra Naura Adnin", "cls": "2 A", "code": "2a"},
            {"name": "Atha Khalif Rahman", "cls": "3 A", "code": "3a"},
            {"name": "Athaya Naura Alima", "cls": "3 A", "code": "3a"},
            {"name": "Bianca Almira Putri", "cls": "4 A", "code": "4a"},
            {"name": "Bima Sakti Pratama", "cls": "4 A", "code": "4a"},
            {"name": "Daffa Almer Putra", "cls": "5 A", "code": "5a"},
            {"name": "Daniswara Putri", "cls": "5 A", "code": "5a"},
            {"name": "Elang Mahardika", "cls": "6 A", "code": "6a"},
            {"name": "Erlangga Aditya", "cls": "6 A", "code": "6a"},
        ]
    return students

STUDENTS = load_students()

# ==================== WEBSOCKET SERVER ====================
connected_clients = set()

async def ws_handler(websocket):
    connected_clients.add(websocket)
    addr = websocket.remote_address
    print(f"  ✅ Browser connected: {addr}")
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data.get("type") == "hello":
                print(f"  👋 Hello from browser")
            elif data.get("type") == "ack":
                print(f"  ✅ Browser received: {data.get('name', '?')}")
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"  ❌ Browser disconnected: {addr}")

async def broadcast(message):
    """Send to all connected browsers (index.html)"""
    if not connected_clients:
        return False
    data = json.dumps(message)
    await asyncio.gather(*[client.send(data) for client in connected_clients], return_exceptions=True)
    return True

# ==================== TEST ACTIONS ====================
called_history = set()

async def call_student(name, delay=0):
    """Call a single student by name"""
    student = next((s for s in STUDENTS if s["name"].lower() == name.lower()), None)
    if not student:
        # Try partial match
        matches = [s for s in STUDENTS if name.lower() in s["name"].lower()]
        if len(matches) == 1:
            student = matches[0]
        elif len(matches) > 1:
            print(f"  ⚠️  Multiple matches: {[s['name'] for s in matches[:5]]}")
            return None
        else:
            print(f"  ❌ Not found: {name}")
            return None
    
    if delay > 0:
        await asyncio.sleep(delay / 1000.0)
    
    msg = {"type": "call", "name": student["name"], "cls": student["cls"], "code": student["code"], "ts": time.time()}
    sent = await broadcast(msg)
    if sent:
        print(f"  📱 Called: {student['name']} ({student['cls']})")
    else:
        print(f"  ⚠️  No browser connected! Open index.html first.")
    return student

async def bulk_call(n):
    """Call n random students simultaneously"""
    available = [s for s in STUDENTS if s["name"] not in called_history]
    if len(available) < n:
        called_history.clear()
        available = STUDENTS.copy()
    
    selected = random.sample(available, min(n, len(available)))
    for s in selected:
        called_history.add(s["name"])
    
    print(f"\n💣 BULK: Calling {len(selected)} students simultaneously...")
    tasks = [call_student(s["name"]) for s in selected]
    results = await asyncio.gather(*tasks)
    print(f"✅ BULK done: {len([r for r in results if r])} sent\n")
    return results

async def rapid_fire(n, delay_ms=100):
    """Call n students sequentially with delay"""
    available = [s for s in STUDENTS if s["name"] not in called_history]
    if len(available) < n:
        called_history.clear()
        available = STUDENTS.copy()
    
    selected = random.sample(available, min(n, len(available)))
    for s in selected:
        called_history.add(s["name"])
    
    print(f"\n⚡ RAPID: {len(selected)} students, {delay_ms}ms delay...")
    for i, s in enumerate(selected):
        await call_student(s["name"], delay=0)
        print(f"  [{i+1}/{len(selected)}] {s['name']}")
        if i < len(selected) - 1:
            await asyncio.sleep(delay_ms / 1000.0)
    print(f"✅ RAPID done\n")

async def stress_test():
    """Run a comprehensive stress test"""
    print("\n" + "="*60)
    print("🧪 STRESS TEST - Pemanggilan Siswa SD Priangan Istiqamah")
    print("="*60)
    
    if not connected_clients:
        print("❌ No browser connected! Open index.html first.")
        return
    
    # Test 1: Single call
    print("\n📋 Test 1: Single call")
    s = random.choice(STUDENTS)
    await call_student(s["name"])
    await asyncio.sleep(1.5)
    
    # Test 2: Bulk 5
    print("\n📋 Test 2: Bulk 5 students")
    await bulk_call(5)
    await asyncio.sleep(3)
    
    # Test 3: Rapid 8
    print("\n📋 Test 3: Rapid fire 8 students (80ms)")
    await rapid_fire(8, 80)
    await asyncio.sleep(3)
    
    # Test 4: Bulk 10 (stress)
    print("\n📋 Test 4: Stress - Bulk 10 students")
    await bulk_call(10)
    await asyncio.sleep(3)
    
    # Test 5: Rapid 15 (max stress)
    print("\n📋 Test 5: Max stress - Rapid 15 students (30ms)")
    await rapid_fire(15, 30)
    
    print("\n" + "="*60)
    print("✅ STRESS TEST COMPLETE!")
    print("="*60 + "\n")

async def clear_all():
    await broadcast({"type": "clear"})
    called_history.clear()
    print("🗑  Clear command sent")

# ==================== HTTP SERVER (for test page) ====================
class TestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)
    
    def do_GET(self):
        if self.path == "/test":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = get_test_page()
            self.wfile.write(html.encode())
        else:
            super().do_GET()

def get_test_page():
    students_json = json.dumps(STUDENTS[:30])  # first 30 for the page
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧪 Python Test Controller</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:system-ui,sans-serif; background:#1a1a2e; color:#eee; padding:20px; }}
h1 {{ font-size:1.2rem; margin-bottom:4px; }}
.sub {{ color:#888; font-size:.75rem; margin-bottom:16px; }}
.card {{ background:#16213e; border-radius:10px; padding:14px; margin-bottom:10px; border:1px solid #0f3460; }}
.card h3 {{ color:#e94560; font-size:.85rem; margin-bottom:8px; }}
.btn {{ padding:8px 14px; border:none; border-radius:6px; cursor:pointer; font-weight:600; font-size:.75rem; margin:2px; }}
.btn:active {{ transform:scale(.95); }}
.btn-fire {{ background:#e94560; color:#fff; }}
.btn-bulk {{ background:#f39c12; color:#fff; }}
.btn-rapid {{ background:#e74c3c; color:#fff; }}
.btn-clear {{ background:#333; color:#ccc; }}
.status {{ display:inline-block; padding:3px 10px; border-radius:10px; font-size:.7rem; }}
.status-ok {{ background:#1a3a1a; color:#3fb950; }}
.status-err {{ background:#3a1a1a; color:#f85149; }}
.flex {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.log {{ background:#0d1117; border-radius:8px; padding:10px; max-height:200px; overflow-y:auto; font-family:monospace; font-size:.7rem; }}
input {{ padding:6px 8px; border-radius:4px; border:1px solid #0f3460; background:#0d1117; color:#eee; font-size:.75rem; }}
input[type=number] {{ width:55px; }}
</style>
</head>
<body>
<h1>🧪 Python Test Controller</h1>
<p class="sub">WebSocket → ws://localhost:{PORT_WS} | HTTP → :{PORT_HTTP}</p>

<div class="card">
  <h3>📡 Koneksi</h3>
  <div class="flex">
    <span>Browser:</span>
    <span class="status status-err" id="wsStatus">● Menghubungkan...</span>
    <span style="font-size:.7rem;color:#888" id="studentCount"></span>
  </div>
</div>

<div class="card">
  <h3>🎯 Single Call</h3>
  <input type="text" id="singleName" placeholder="Nama siswa..." style="width:200px">
  <button class="btn btn-fire" onclick="callSingle()">📢 Panggil</button>
</div>

<div class="card">
  <h3>💣 Bulk Call</h3>
  <div class="flex">
    <input type="number" id="bulkCount" value="5" min="1" max="50"> <span>siswa</span>
    <button class="btn btn-bulk" onclick="callBulk()">💥 Bulk</button>
  </div>
</div>

<div class="card">
  <h3>⚡ Rapid Fire</h3>
  <div class="flex">
    <input type="number" id="rapidCount" value="8" min="1" max="30"> <span>siswa, jeda</span>
    <input type="number" id="rapidDelay" value="80" min="10" max="5000"> <span>ms</span>
    <button class="btn btn-rapid" onclick="callRapid()">⚡ Rapid</button>
  </div>
</div>

<div class="card">
  <h3>🧹 Clear</h3>
  <button class="btn btn-clear" onclick="sendCmd('clear')">🗑 Clear Queue</button>
</div>

<div class="card">
  <h3>📋 Log</h3>
  <div class="log" id="log"></div>
</div>

<script>
const STUDENTS = {students_json};
const WS_URL = 'ws://localhost:{PORT_WS}';
let ws;

function log(msg, cls) {{
  const el = document.getElementById('log');
  el.innerHTML += `<div class="${{cls||''}}">[${{new Date().toLocaleTimeString()}}] ${{msg}}</div>`;
  el.scrollTop = el.scrollHeight;
}}

function connect() {{
  ws = new WebSocket(WS_URL);
  ws.onopen = () => {{
    document.getElementById('wsStatus').textContent = '● Terhubung';
    document.getElementById('wsStatus').className = 'status status-ok';
    ws.send(JSON.stringify({{type:'hello'}}));
    log('✅ Connected to Python server', 'ok');
  }};
  ws.onclose = () => {{
    document.getElementById('wsStatus').textContent = '● Terputus';
    document.getElementById('wsStatus').className = 'status status-err';
    log('⚠️ Disconnected, retrying...', 'err');
    setTimeout(connect, 2000);
  }};
  ws.onmessage = (e) => {{
    const data = JSON.parse(e.data);
    if (data.type === 'ack') log('📥 ' + data.name, 'ok');
  }};
}}

function sendCmd(cmd) {{
  if (ws && ws.readyState === WebSocket.OPEN) {{
    ws.send(JSON.stringify({{type:cmd}}));
  }}
}}

function callSingle() {{
  const name = document.getElementById('singleName').value.trim();
  if (!name) return;
  const s = STUDENTS.find(x => x.name.toLowerCase().includes(name.toLowerCase()));
  if (!s) {{ log('❌ Not found: ' + name, 'err'); return; }}
  ws.send(JSON.stringify({{type:'call_one', name:s.name}}));
  log('📱 Calling: ' + s.name, 'ok');
}}

function callBulk() {{
  const n = parseInt(document.getElementById('bulkCount').value) || 5;
  ws.send(JSON.stringify({{type:'bulk', n:n}}));
  log('💣 Bulk: ' + n + ' students', 'ok');
}}

function callRapid() {{
  const n = parseInt(document.getElementById('rapidCount').value) || 8;
  const d = parseInt(document.getElementById('rapidDelay').value) || 80;
  ws.send(JSON.stringify({{type:'rapid', n:n, delay:d}}));
  log('⚡ Rapid: ' + n + ' students, ' + d + 'ms', 'ok');
}}

document.getElementById('studentCount').textContent = '(' + STUDENTS.length + ' siswa)';
connect();
log('🧪 Test controller ready', 'ok');
</script>
</body>
</html>"""

# ==================== COMMAND HANDLER ====================
async def handle_ws_command(data):
    msg = json.loads(data)
    cmd = msg.get("type", "")
    
    if cmd == "hello":
        print("  👋 Test controller connected")
    elif cmd == "call_one":
        await call_student(msg["name"])
    elif cmd == "bulk":
        await bulk_call(int(msg.get("n", 5)))
    elif cmd == "rapid":
        await rapid_fire(int(msg.get("n", 8)), int(msg.get("delay", 100)))
    elif cmd == "clear":
        await clear_all()

# Wrapper for WebSocket handler to handle both browser and test controller
async def ws_handler_combined(websocket):
    connected_clients.add(websocket)
    addr = websocket.remote_address
    print(f"  ✅ Connected: {addr}")
    try:
        async for msg in websocket:
            data = json.loads(msg)
            t = data.get("type", "")
            if t in ("hello", "ack"):
                # browser messages
                if t == "hello":
                    print(f"  👋 Browser hello")
            elif t in ("call_one", "bulk", "rapid", "clear"):
                # test controller commands
                await handle_ws_command(msg)
            else:
                print(f"  ❓ Unknown: {t}")
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"  ❌ Disconnected: {addr}")

# ==================== CLI ====================
def print_help():
    print("""
╔══════════════════════════════════════════════════════╗
║  🧪 STRESS TEST TOOL - Pemanggilan Siswa SDPI       ║
╠══════════════════════════════════════════════════════╣
║  Commands:                                          ║
║    call <nama>      Panggil 1 siswa                 ║
║    bulk <n>         Panggil n siswa bersamaan       ║
║    rapid <n> [ms]   Panggil n siswa beruntun        ║
║    list             Tampilkan semua siswa            ║
║    clear            Reset antrian                    ║
║    stress           Jalankan full stress test        ║
║    help             Tampilkan bantuan                ║
║    quit             Keluar                           ║
╚══════════════════════════════════════════════════════╝
""")

async def cli_loop():
    """Interactive CLI for manual testing"""
    print_help()
    print(f"  📋 {len(STUDENTS)} students loaded")
    print(f"  🔌 WebSocket server: ws://localhost:{PORT_WS}")
    print(f"  🌐 Test controller: http://localhost:{PORT_HTTP}/test")
    print(f"  💡 Buka index.html di browser, lalu ketik perintah di sini\n")
    
    while True:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(None, input, "  > ")
            cmd = cmd.strip()
            if not cmd:
                continue
            
            parts = cmd.split()
            action = parts[0].lower()
            
            if action == "quit" or action == "exit":
                print("  👋 Bye!")
                break
            elif action == "help":
                print_help()
            elif action == "list":
                print(f"  📋 {len(STUDENTS)} siswa:")
                for s in STUDENTS:
                    print(f"     • {s['name']} ({s['cls']})")
            elif action == "call":
                if len(parts) < 2:
                    print("  ❌ Usage: call <nama>")
                else:
                    name = " ".join(parts[1:])
                    await call_student(name)
            elif action == "bulk":
                n = int(parts[1]) if len(parts) > 1 else 5
                await bulk_call(n)
            elif action == "rapid":
                n = int(parts[1]) if len(parts) > 1 else 8
                delay = int(parts[2]) if len(parts) > 2 else 100
                await rapid_fire(n, delay)
            elif action == "clear":
                await clear_all()
            elif action == "stress":
                await stress_test()
            elif action == "test":
                await stress_test()
            else:
                print(f"  ❌ Unknown command: {action}")
                print(f"  💡 Type 'help' for commands")
        except KeyboardInterrupt:
            print("\n  👋 Interrupted!")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")

# ==================== MAIN ====================
async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║  🧪 STRESS TEST TOOL - Pemanggilan Siswa SDPI       ║
║  WebSocket + HTTP Server                            ║
╚══════════════════════════════════════════════════════╝
""")
    print(f"  📋 Loaded {len(STUDENTS)} students from siswa.txt")
    print(f"  🔌 WebSocket: ws://localhost:{PORT_WS}")
    print(f"  🌐 HTTP: http://localhost:{PORT_HTTP}")
    print(f"  🧪 Test page: http://localhost:{PORT_HTTP}/test")
    print(f"  💡 Buka index.html di browser, lalu ketik perintah\n")
    
    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler_combined, "localhost", PORT_WS)
    print(f"  ✅ WebSocket server running on ws://localhost:{PORT_WS}")
    
    # Start HTTP server in a thread
    httpd = HTTPServer(("localhost", PORT_HTTP), TestHandler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()
    print(f"  ✅ HTTP server running on http://localhost:{PORT_HTTP}")
    
    print(f"  ⏳ Waiting for index.html to connect...\n")
    
    # Run CLI
    await cli_loop()
    
    # Cleanup
    ws_server.close()
    await ws_server.wait_closed()
    httpd.shutdown()
    print("  ✅ Servers stopped")

if __name__ == "__main__":
    asyncio.run(main())