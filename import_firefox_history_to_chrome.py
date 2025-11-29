#!/usr/bin/env python3
# import_firefox_history_to_chrome.py
# Usage:
#   python3 import_firefox_history_to_chrome.py --csv firefox_history_.csv --chrome-history "/path/to/History" [--dry-run]

import sqlite3, csv, argparse, os, shutil, time, sys

EPOCH_DIFF_SECONDS = 11644473600  # seconds between 1601-01-01 and 1970-01-01
US_PER_SECOND = 1000000
WEBKIT_EPOCH_DIFF_US = EPOCH_DIFF_SECONDS * US_PER_SECOND

def parse_args():
    p = argparse.ArgumentParser(description="Import Firefox history CSV into Chrome History DB")
    p.add_argument('--csv', required=True, help='Path to firefox_history_extraction.csv')
    p.add_argument('--chrome-history', required=True, help='Path to Chrome History sqlite file')
    p.add_argument('--dry-run', action='store_true', help='Do not modify DB; just report counts')
    return p.parse_args()

def backup_file(path):
    bak = path + '.bak.' + time.strftime('%Y%m%d%H%M%S')
    shutil.copy2(path, bak)
    print(f"Backup created: {bak}")
    return bak

def chrome_time_from_firefox_us(ff_us):
    return int(ff_us) + WEBKIT_EPOCH_DIFF_US

def main():
    args = parse_args()
    csv_path = os.path.expanduser(args.csv)
    chrome_db = os.path.expanduser(args.chrome_history)

    if not os.path.exists(csv_path):
        print("CSV not found:", csv_path); sys.exit(1)
    if not os.path.exists(chrome_db):
        print("Chrome History DB not found:", chrome_db); sys.exit(1)

    # read CSV
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            url = r.get('url','').strip()
            if not url: continue
            try:
                ff_us = int(r['visit_date_us'])
            except Exception:
                continue
            chrome_us = chrome_time_from_firefox_us(ff_us)
            title = r.get('title','')
            rows.append((url, title, chrome_us))

    print(f"CSV rows parsed: {len(rows)}")

    # connect to chrome db
    conn = sqlite3.connect(chrome_db)
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = ON;')

    if args.dry_run:
        # Estimate how many would be inserted vs duplicates
        inserts = 0
        duplicates = 0
        for url, title, c_us in rows:
            cur.execute('SELECT id FROM urls WHERE url = ?;', (url,))
            row = cur.fetchone()
            if row:
                url_id = row[0]
            else:
                url_id = None
            if url_id:
                cur.execute('SELECT 1 FROM visits WHERE url = ? AND visit_time = ? LIMIT 1;', (url_id, c_us))
                if cur.fetchone():
                    duplicates += 1
                else:
                    inserts += 1
            else:
                inserts += 1
        print(f"[DRY-RUN] Would insert visits: {inserts}, duplicates skipped: {duplicates}")
        conn.close()
        return

    # backup chrome db
    backup_file(chrome_db)

    try:
        conn.execute('BEGIN;')
        inserted_visits = 0
        skipped_duplicates = 0
        urls_added = 0
        for url, title, c_us in rows:
            cur.execute('SELECT id FROM urls WHERE url = ?;', (url,))
            row = cur.fetchone()
            if row:
                url_id = row[0]
            else:
                cur.execute('INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time) VALUES (?, ?, 0, 0, ?);', (url, title, c_us))
                url_id = cur.lastrowid
                urls_added += 1

            cur.execute('SELECT 1 FROM visits WHERE url = ? AND visit_time = ? LIMIT 1;', (url_id, c_us))
            if cur.fetchone():
                skipped_duplicates += 1
                continue

            cur.execute('INSERT INTO visits (url, visit_time, from_visit, transition) VALUES (?, ?, 0, 0);', (url_id, c_us))
            inserted_visits += 1

        # update visit_count and last_visit_time
        cur.execute('''
            UPDATE urls SET
                visit_count = (SELECT COUNT(*) FROM visits WHERE visits.url = urls.id),
                last_visit_time = COALESCE((SELECT MAX(visit_time) FROM visits WHERE visits.url = urls.id), 0)
        ''')
        conn.commit()
        print(f"Inserted visits: {inserted_visits}, URLs added: {urls_added}, Duplicates skipped: {skipped_duplicates}")
    except Exception as e:
        conn.rollback()
        print("Error during import, rolled back. Error:", e)
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
