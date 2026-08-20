import sqlite3
import os
import glob
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "alpha.db")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")
MAX_BACKUPS = 3

def perform_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Database file {DB_PATH} not found!")
        return

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"alpha_backup_{now_str}.db")

    # Safe SQLite online backup
    try:
        source_conn = sqlite3.connect(DB_PATH)
        dest_conn = sqlite3.connect(backup_file)
        with dest_conn:
            source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        file_size_kb = round(os.path.getsize(backup_file) / 1024, 2)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Backup successful: {os.path.basename(backup_file)} ({file_size_kb} KB)")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Backup failed: {e}")
        return

    # Clean up older backups (keep only last MAX_BACKUPS = 3)
    try:
        backup_files = sorted(
            glob.glob(os.path.join(BACKUP_DIR, "alpha_backup_*.db")),
            key=os.path.getmtime
        )
        if len(backup_files) > MAX_BACKUPS:
            to_remove = backup_files[:-MAX_BACKUPS]
            for old_file in to_remove:
                os.remove(old_file)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🗑️ Removed old backup: {os.path.basename(old_file)}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📦 Retained {min(len(backup_files), MAX_BACKUPS)} recent backups.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    perform_backup()
