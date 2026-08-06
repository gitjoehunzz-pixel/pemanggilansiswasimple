"""
🎮 Simulasi Stress Test - Pemanggilan Siswa SD Priangan Istiqamah
================================================================
Tool TERPISAH dari aplikasi utama (index.html).
Simulasi banyak orang tua klik bersamaan & berulang random.

Cara pakai:
  1. Buka index.html di browser
  2. Jalankan script ini: python simulasi.py
  3. Script akan auto-connect ke halaman & mulai simulasi

Requirements:
  pip install playwright
  playwright install chromium
"""

import asyncio
import random
import time
import sys
import os

# Konfigurasi
URL = "http://localhost:8080/index.html"  # Ganti sesuai URL hosting
INTERVAL_MS = 200      # Jarak antar klik (ms) - makin kecil makin cepat
DURATION_SEC = 30      # Lama simulasi (detik)
CONCURRENT = 3         # Jumlah "orang tua" simultan

# ============================================================

STUDENTS = None  # Akan di-load dari halaman

async def get_student_count(page):
    """Ambil jumlah siswa dari halaman"""
    return await page.evaluate("() => STUDENT_DATA.length")

async def get_queue_length(page):
    return await page.evaluate("() => state.queue.length")

async def get_history_length(page):
    return await page.evaluate("() => state.history.length")

async def click_random_student(page):
    """Klik siswa random yang tersedia"""
    try:
        # Cari kartu siswa yang available (bukan dalam queue/called)
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
            # Klik kartu siswa
            await page.click(f'.student-card[data-name="{result}"]')
            return result
    except Exception as e:
        pass
    return None

async def simulate_parent(page, parent_id, interval_ms, duration):
    """Simulasi satu orang tua yang klik terus-menerus"""
    end_time = time.time() + duration
    clicks = 0
    while time.time() < end_time:
        name = await click_random_student(page)
        if name:
            clicks += 1
            if clicks % 10 == 0:
                print(f"  👤 OrangTua-{parent_id}: {clicks} klik | terakhir: {name}")
        await asyncio.sleep(interval_ms / 1000)
    return clicks

async def main():
    print("=" * 60)
    print("🎮 SIMULASI STRESS TEST")
    print("   Pemanggilan Siswa SD Priangan Istiqamah")
    print("=" * 60)
    
    # Cek Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("\n❌ Playwright belum terinstall!")
        print("   Jalankan: pip install playwright")
        print("   Lalu:     playwright install chromium")
        sys.exit(1)
    
    # Cek URL
    print(f"\n🌐 Target: {URL}")
    print(f"⚡ Interval: {INTERVAL_MS}ms | Durasi: {DURATION_SEC}s | Concurrent: {CONCURRENT}")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(URL, timeout=10000)
        except Exception:
            print(f"❌ Tidak bisa connect ke {URL}")
            print("   Pastikan index.html sudah dibuka / di-hosting")
            await browser.close()
            sys.exit(1)
        
        await page.wait_for_timeout(1000)
        
        total = await get_student_count(page)
        print(f"✅ Connected! {total} siswa terdeteksi")
        
        # Start simulasi
        print(f"\n🚀 Mulai simulasi {CONCURRENT} orang tua...")
        print("-" * 40)
        
        start = time.time()
        tasks = [simulate_parent(page, i+1, INTERVAL_MS, DURATION_SEC) for i in range(CONCURRENT)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start
        total_clicks = sum(results)
        
        print("-" * 40)
        print(f"\n📊 HASIL SIMULASI")
        print(f"   Durasi:        {elapsed:.1f}s")
        print(f"   Total klik:    {total_clicks}")
        print(f"   Klik/detik:    {total_clicks/elapsed:.1f}")
        print(f"   Queue sisa:    {await get_queue_length(page)}")
        print(f"   History:       {await get_history_length(page)}")
        print(f"   Per orang tua: {results}")
        print()
        
        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())