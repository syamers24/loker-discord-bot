import os
import json
import requests
import re
from jobspy import scrape_jobs

# 1. Konfigurasi Pencarian Loker
SEARCH_TERMS = [
    "Software Engineer",
    "Cloud Engineer",
    "Data Analyst",
    "Data Engineer",
    "DevOps Engineer"
]
LOCATION = "Indonesia"

# --- TITIK UBAH LIMIT ---
RESULTS_PER_TERM = 3       # Ubah dari 10 menjadi 3 (agar pencarian tidak terlalu luas)
MAX_POSTS_PER_RUN = 5      # Batas MAKSIMAL total pesan yang boleh dikirim ke Discord dalam 1x jalan
PLATFORMS = ["linkedin", "indeed"]   # Opsional: Jika masih terlalu banyak, ciutkan sementara ke LinkedIn saja

SEEN_JOBS_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def generate_fingerprint(title, company):
    """
    Membuat sidik jari unik dari Perusahaan + Judul Loker.
    Contoh: 'Data Engineer - Cloud' di 'PT. Telkom' -> 'pttelkom-dataengineercloud'
    """
    clean_title = re.sub(r'[^a-zA-Z0-9]', '', str(title).lower())
    clean_company = re.sub(r'[^a-zA-Z0-9]', '', str(company).lower())
    return f"{clean_company}-{clean_title}"

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def clean_field(value, default_text):
    """
    Memastikan data bernilai valid (bukan None, NaN, atau teks kosong).
    """
    if pd.isna(value) or value is None:
        return default_text
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null"]:
        return default_text
        
    return val_str

def send_to_discord(job):
    if not DISCORD_WEBHOOK_URL:
        print("Webhook URL tidak ditemukan.")
        return False

    # Bersihkan setiap data dari nilai None / NaN
    title = clean_field(job.get("title"), "Lowongan Kerja Tech")
    company = clean_field(job.get("company"), "Perusahaan")
    location = clean_field(job.get("location"), "Indonesia")
    job_url = clean_field(job.get("job_url"), "")
    date_posted = clean_field(job.get("date_posted"), "Baru saja")
    
    site = clean_field(job.get("site"), "Web").capitalize()

    # Jika job_url kosong, kita tidak bisa mengirim link
    if not job_url:
        print(f"[Skip] URL tidak valid untuk {title}")
        return False

    payload = {
        "embeds": [
            {
                "title": f"💼 {title}",
                "url": job_url,
                "color": 5814783, 
                "fields": [
                    {"name": "🏢 Perusahaan", "value": company, "inline": True},
                    {"name": "📍 Lokasi", "value": location, "inline": True},
                    {"name": "📅 Tanggal Posting", "value": date_posted, "inline": False}
                ],
                "footer": {
                    "text": f"Info Loker Tech Indonesia • Sumber: {site}"
                }
            }
        ]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code in [200, 204]:
        print(f"[Terkirim] {site} | {company} - {title}")
        return True
    else:
        print(f"[Gagal Kirim] Status {response.status_code}: {response.text}")
        return False

def main():
    seen_jobs = load_seen_jobs()
    new_jobs_count = 0

    print("Memulai pengambilan lowongan dari beberapa platform...")

    for term in SEARCH_TERMS:
        # Hentikan pencarian jika batas maksimal postingan sudah tercapai
        if new_jobs_count >= MAX_POSTS_PER_RUN:
            print(f"Batas maksimal {MAX_POSTS_PER_RUN} postingan per sesi telah tercapai. Menghentikan proses.")
            break

        print(f"\nMencari role: {term}...")
        try:
            jobs = scrape_jobs(
                site_name=PLATFORMS,
                search_term=term,
                location=LOCATION,
                results_wanted=RESULTS_PER_TERM,
                hours_old=24,
                country_indeed='indonesia'
            )

            if jobs.empty:
                print(f"Tidak ada loker baru untuk {term}.")
                continue

            for _, job in jobs.iterrows():
                # Hentikan loop jika di tengah jalan sudah mencapai batas
                if new_jobs_count >= MAX_POSTS_PER_RUN:
                    break

                fingerprint = generate_fingerprint(job.get("title"), job.get("company"))
                
                if fingerprint and fingerprint not in seen_jobs:
                    success = send_to_discord(job)
                    if success:
                        seen_jobs.add(fingerprint)
                        new_jobs_count += 1

        except Exception as e:
            print(f"Error saat mencari {term}: {e}")

    # Simpan kembali daftar sidik jari yang sudah diperbarui
    save_seen_jobs(seen_jobs)
    print(f"\nSelesai! Total {new_jobs_count} lowongan baru berhasil dikirim ke Discord.")

if __name__ == "__main__":
    main()
