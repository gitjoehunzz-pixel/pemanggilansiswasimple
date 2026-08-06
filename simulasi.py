"""
🎮 Simulasi Stress Test - Multi-User + Multi-IP
================================================================
Target: https://pemanggilansiswasimple.vercel.app/

Simulasi banyak user berbeda (isolated localStorage) klik bersamaan,
seperti orang tua dari device berbeda.

Cara pakai:
  pip install playwright
  playwright install chromium
  python simulasi.py
  python simulasi.py --users 20 --duration 60 --headless
  python simulasi.py --users 50 --burst --headless
"""

import asyncio
import random
import time
import sys
import argparse
from datetime import datetime

# ============================================================
DEFAULT_URL = "https://pemanggilansiswasimple.vercel.app/"
DEFAULT_USERS = 10
DEFAULT_DURATION = 30
DEFAULT_INTERVAL = 200

# ============================================================

def parse_args():
    p = argparse.ArgumentParser(description="Stress test multi-user pemanggilan siswa")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--users", type=int, default=DEFAULT_USERS, help="Jumlah user simultan")
    p.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Durasi (detik)")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Interval klik (ms)")
    p.add_argument("--headless", action="store_true", help="Tanpa UI browser")
    p.add_argument("--burst", action="store_true", help="Burst mode: klik 5-10 sekaligus")
    return p.parse_args()

class UserSimulator:
    """Satu user = satu browser context (isolated localStorage)"""
    
    def __init__(self, uid, browser, url, interval_ms, burst_mode):
        self.uid = uid
        self.browser = browser
        self.url = url
        self.interval_ms = interval_ms
        self.burst_mode = burst_mode
        self.page = None
        self.context = None
        self.clicks = 0
        self.errors = 0
    
    async def start(self):
        """Buka halaman & siapkan"""
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="id-ID",
            # Simulasi user agent berbeda
            user_agent=f"Mozilla/5.0 User{self.uid}/1.0"
        )
        self.page = await self.context.new_page()
        try:
            await self.page.goto(self.url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            # Klik untuk unlock audio
            await self.page.click("body", position={"x": 10, "y": 10})
            # Tutup resume banner jika ada
            try:
                banner = await self.page.query_selector("#resumeBanner")
                if banner:
                    await banner.click()
            except:
                pass
            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            self.errors += 1
            return False
    
    async def click_random(self):
        """Klik satu siswa random"""
        try:
            name = await self.page.evaluate("""() => {
                const available = STUDENT_DATA.filter(s => {
                    const inQueue = state.queue.some(q => q.name === s.name);
                    const isCurrent = state.current && state.current.name === s.name;
                    return !inQueue && !isCurrent;
                });
                if (available.length === 0) return null;
                return available[Math.floor(Math.random() * available.length)].name;
            }""")
            if name:
                await self.page.click(f'.student-card[data-name="{name}"]')
                self.clicks += 1
                return True
        except:
            self.errors += 1
        return False
    
    async def burst_click(self):
        """Klik 5-10 siswa sekaligus"""
        count = random.randint(5, 10)
        success = 0
        for _ in range(count):
            if await self.click_random():
                success += 1
        return success
    
    async def run(self, duration):
        """Jalankan simulasi"""
        end = time.time() + duration
        while time.time() < end:
            if self.burst_mode:
                n = await self.burst_click()
                if n > 0 and self.clicks % 50 == 0:
                    stats = await self.get_stats()
                    print(f"  👤 U{self.uid:03d}: {self.clicks} klik | Q:{stats['q']} | H:{stats['h']}")
            else:
                if await self.click_random():
                    if self.clicks % 20 == 0:
                        stats = await self.get_stats()
                        print(f"  👤 U{self.uid:03d}: {self.clicks} klik | Q:{stats['q']} | H:{stats['h']}")
            
            jitter = self.interval_ms * random.uniform(0.6, 1.4)
            await asyncio.sleep(jitter / 1000)
    
    async def get_stats(self):
        try:
            return await self.page.evaluate("""() => ({
                q: state.queue.length,
                h: state.history.length,
                p: state.isPlaying
            })""")
        except:
            return {"q": "?", "h": "?", "p": False}
    
    async def stop(self):
        if self.context:
            await self.context.close()

async def main():
    args = parse_args()
    
    print("=" * 65)
    print("🎮 STRESS TEST - MULTI USER")
    print("   Pemanggilan Siswa SD Priangan Istiqamah")
    print("=" * 65)
    print(f"   🌐 URL:       {args.url}")
    print(f"   👥 Users:     {args.users} (isolated sessions)")
    print(f"   ⏱  Duration:  {args.duration}s")
    print(f"   ⚡ Interval:  {args.interval}ms")
    print(f"   🥷 Headless:  {args.headless}")
    print(f"   💥 Burst:     {args.burst}")
    print("=" * 65)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("\n❌ pip install playwright && playwright install chromium")
        sys.exit(1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        
        # Buat semua user
        print(f"\n🔗 Membuka {args.users} session...")
        users = []
        for i in range(args.users):
            u = UserSimulator(i+1, browser, args.url, args.interval, args.burst)
            users.append(u)
        
        # Start semua user secara paralel (batch per 5 agar tidak overload)
        batch_size = 5
        started = 0
        for batch_start in range(0, len(users), batch_size):
            batch = users[batch_start:batch_start+batch_size]
            results = await asyncio.gather(*[u.start() for u in batch])
            started += sum(results)
            print(f"   ✅ {started}/{len(users)} user siap")
            await asyncio.sleep(0.5)
        
        print(f"\n🚀 MULAI SIMULASI! {started} user, {args.duration}s")
        print(f"   Mode: {'💥 BURST' if args.burst else '🔄 Reguler'}")
        print("-" * 65)
        
        start_time = time.time()
        await asyncio.gather(*[u.run(args.duration) for u in users if u.page])
        elapsed = time.time() - start_time
        
        # Stop semua
        await asyncio.gather(*[u.stop() for u in users])
        await browser.close()
        
        # Hasil
        total_clicks = sum(u.clicks for u in users)
        total_errors = sum(u.errors for u in users)
        
        print("-" * 65)
        print(f"\n📊 HASIL STRESS TEST")
        print(f"   ⏱  Durasi:       {elapsed:.1f}s")
        print(f"   👥 Users aktif:  {started}")
        print(f"   🖱  Total klik:   {total_clicks}")
        print(f"   ⚡ Klik/detik:    {total_clicks/elapsed:.1f}")
        print(f"   ❌ Errors:       {total_errors}")
        print(f"   📈 Avg/user:     {total_clicks/started:.0f} klik")
        print(f"   🕐 Selesai:      {datetime.now().strftime('%H:%M:%S')}")
        print()

if __name__ == "__main__":
    asyncio.run(main())