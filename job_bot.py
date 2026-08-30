import os
import json
import requests
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
RESULTS_PER_TERM = 10  # Jumlah loker yang dicari per kata kunci
SEEN_JOBS_FILE = "seen_jobs.json"

# Read Webhook URL dari GitHub Secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def load_seen_jobs():
    """Membaca ID loker yang sudah pernah dikirim agar tidak duplikat."""
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error membaca {SEEN_JOBS_FILE}: {e}")
            return set()
    return set()

def save_seen_jobs(seen_jobs):
    """Menyimpan ID loker terbaru ke file JSON."""
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def send_to_discord(job):
    """Mengirim info loker ke Discord channel menggunakan Embed yang rapi."""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL tidak ditemukan pada Environment Variables.")
        return False

    title = job.get("title", "Lowongan Baru")
    company = job.get("company", "Perusahaan Tidak Diketahui")
    location = job.get("location", "Indonesia")
    job_url = job.get("job_url", "")
    date_posted = job.get("date_posted", "Baru saja")

    payload = {
        "embeds": [
            {
                "title": f"💼 {title}",
                "url": job_url,
                "color": 3447003,  # Warna Biru khas LinkedIn
                "fields": [
                    {"name": "🏢 Perusahaan", "value": str(company), "inline": True},
                    {"name": "📍 Lokasi", "value": str(location), "inline": True},
                    {"name": "📅 Tanggal Posting", "value": str(date_posted), "inline": False}
                ],
                "footer": {
                    "text": "Info Loker Tech Indonesia • LinkedIn"
                }
            }
        ]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code in [200, 204]:
        print(f"[Berhasil Dikirim] {title} - {company}")
        return True
    else:
        print(f"[Gagal Kirim] Status Code {response.status_code}: {response.text}")
        return False

def main():
    seen_jobs = load_seen_jobs()
    new_jobs_count = 0

    print("Memulai pengambilan lowongan dari LinkedIn...")

    for term in SEARCH_TERMS:
        print(f"\nMencari role: {term}...")
        try:
            # Menggunakan JobSpy untuk mengambil loker 24 jam terakhir dari LinkedIn
            jobs = scrape_jobs(
                site_name=["linkedin"],
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
                job_id = str(job.get("id"))
                
                # Jika loker belum pernah dikirim ke Discord
                if job_id and job_id not in seen_jobs:
                    success = send_to_discord(job)
                    if success:
                        seen_jobs.add(job_id)
                        new_jobs_count += 1

        except Exception as e:
            print(f"Error saat mengeksekusi pencarian {term}: {e}")

    # Simpan kembali ID yang sudah terkirim
    save_seen_jobs(seen_jobs)
    print(f"\nSelesai! {new_jobs_count} lowongan baru berhasil dikirim ke Discord.")

if __name__ == "__main__":
    main()
