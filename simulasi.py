"""
🎮 Simulasi Stress Test - Pemanggilan Siswa SD Priangan Istiqamah
================================================================
Simulasi banyak orang tua klik bersamaan & berulang random.
Target: Vercel hosting (https://pemanggilansiswasimple.vercel.app/)

Cara pakai:
  1. pip install playwright
  2. playwright install chromium
  3. python simulasi.py
  4. python simulasi.py --headless --concurrent 10 --duration 60

Arguments:
  --url         URL target (default: https://pemanggilansiswasimple.vercel.app/)
  --concurrent  Jumlah orang tua simultan (default: 5)
  --duration    Lama simulasi dalam detik (default: 30)
  --interval    Jarak antar klik ms (default: 150)
  --headless    Mode headless tanpa browser UI
  --burst       Burst mode: klik serentak banyak sekaligus
"""

import asyncio
import random
import time
import sys
import argparse
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
DEFAULT_URL = "https://pemanggilansiswasimple.vercel.app/"
DEFAULT_CONCURRENT = 5
DEFAULT_DURATION = 30
DEFAULT_INTERVAL = 150

# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Stress test pemanggilan siswa")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL target")
    parser.add_argument("--concurrent", type=int, default=DEFAULT_CONCURRENT, help="Orang tua simultan")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Durasi (detik)")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Interval klik (ms)")
    parser.add_argument("--headless", action="store_true", help="Mode headless")
    parser.add_argument("--burst", action="store_true", help="Burst mode: klik serentak")
    return parser.parse_args()

async def get_stats(page):
    """Ambil statistik dari halaman"""
    try:
        return await page.evaluate("""() => ({
            total: STUDENT_DATA.length,
            queue: state.queue.length,
            history: state.history.length,
            isPlaying: state.isPlaying,
            current: state.current ? state.current.name : null
        })""")
    except:
        return None

async def click_random_student(page):
    """Klik siswa random yang tersedia"""
    try:
        result = await page.evaluate("""() => {
            const available = STUDENT_DATA.filter(s => {
                const inQueue = state.queue.some(q => q.name === s.name);
                const isCurrent = state.current && state.current.name === s.name;
                return !inQueue && !isCurrent;
            });
            if (available.length === 0) return null;
            const s = available[Math.floor(Math.random() * available.length)];
            return s.name;
        }""")
        if result:
            await page.click(f'.student-card[data-name="{result}"]')
            return result
    except:
        pass
    return None

async def burst_click(page, count=5):
    """Klik serentak sekaligus"""
    clicks = []
    for _ in range(count):
        name = await click_random_student(page)
        if name:
            clicks.append(name)
    return clicks

async def simulate_parent(page, pid, interval_ms, duration, burst_mode):
    """Simulasi satu orang tua"""
    end_time = time.time() + duration
    clicks = 0
    last_log = time.time()
    
    while time.time() < end_time:
        if burst_mode:
            # Burst: klik 3-8 siswa sekaligus setiap interval
            burst_size = random.randint(3, 8)
            names = await burst_click(page, burst_size)
            clicks += len(names)
            if names and time.time() - last_log > 2:
                print(f"  👤 OT-{pid:02d}: {clicks} klik | burst {len(names)} | antri: {len(names)}")
                last_log = time.time()
        else:
            name = await click_random_student(page)
            if name:
                clicks += 1
                if clicks % 20 == 0:
                    stats = await get_stats(page)
                    q = stats['queue'] if stats else '?'
                    print(f"  👤 OT-{pid:02d}: {clicks} klik | antrian: {q}")
        
        # Random jitter ±30%
        jitter = interval_ms * random.uniform(0.7, 1.3)
        await asyncio.sleep(jitter / 1000)
    
    return clicks

async def main():
    args = parse_args()
    
    print("=" * 60)
    print("🎮 SIMULASI STRESS TEST")
    print("   Pemanggilan Siswa SD Priangan Istiqamah")
    print("=" * 60)
    print(f"   🌐 {args.url}")
    print(f"   👥 Concurrent: {args.concurrent}")
    print(f"   ⏱  Duration: {args.duration}s")
    print(f"   ⚡ Interval: {args.interval}ms")
    print(f"   🥷 Headless: {args.headless}")
    print(f"   💥 Burst: {args.burst}")
    print("=" * 60)
    
    # Cek Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("\n❌ Playwright belum terinstall!")
        print("   pip install playwright")
        print("   playwright install chromium")
        sys.exit(1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="id-ID"
        )
        page = await context.new_page()
        
        # Connect
        print(f"\n🔗 Connecting to {args.url}...")
        try:
            await page.goto(args.url, timeout=15000, wait_until="networkidle")
        except Exception as e:
            print(f"❌ Gagal connect: {e}")
            await browser.close()
            sys.exit(1)
        
        await asyncio.sleep(2)
        
        # Unlock audio (klik di mana saja)
        await page.click("body", position={"x": 10, "y": 10})
        await asyncio.sleep(0.5)
        
        # Cek banner resume & klik jika ada
        try:
            banner = await page.query_selector("#resumeBanner")
            if banner:
                await banner.click()
                await asyncio.sleep(0.5)
        except:
            pass
        
        stats = await get_stats(page)
        if stats:
            print(f"✅ Connected! {stats['total']} siswa | queue: {stats['queue']} | history: {stats['history']}")
        else:
            print("✅ Connected!")
        
        # RUN SIMULATION
        print(f"\n🚀 Mulai simulasi {args.concurrent} orang tua...")
        print(f"   Mode: {'💥 BURST' if args.burst else '🔄 Reguler'}")
        print("-" * 60)
        
        start_time = time.time()
        tasks = [
            simulate_parent(page, i+1, args.interval, args.duration, args.burst)
            for i in range(args.concurrent)
        ]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        total_clicks = sum(results)
        
        # Final stats
        final_stats = await get_stats(page)
        
        print("-" * 60)
        print(f"\n📊 HASIL AKHIR")
        print(f"   ⏱  Durasi:        {elapsed:.1f}s")
        print(f"   🖱  Total klik:    {total_clicks}")
        print(f"   ⚡ Klik/detik:     {total_clicks/elapsed:.1f}")
        if final_stats:
            print(f"   📋 Queue sisa:    {final_stats['queue']}")
            print(f"   📝 History:       {final_stats['history']}")
        print(f"   👤 Per orang tua: {results}")
        print(f"   🕐 Selesai:       {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        await asyncio.sleep(2)
        await browser.close()
        
        print("✅ Simulasi selesai!")

if __name__ == "__main__":
    asyncio.run(main())