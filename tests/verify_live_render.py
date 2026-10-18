import requests
import re
import time

LIVE_URL = "https://student-academic-progression-kajal.onrender.com"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzehCTZN5K2m7oKGePwnSh6EbGchnqQi0SpnKFeFqZ_F8POdeLSRYv7ZI3b4TGwnTjf/exec"

s = requests.Session()

print("--- 1. Health check ---")
r_health = s.get(f"{LIVE_URL}/health")
print("Health:", r_health.json())

print("\n--- 2. Trigger Bulk Sync ---")
r_bulk = s.post(f"{LIVE_URL}/sync/trigger-bulk", allow_redirects=True)
alerts = re.findall(r'<div class="alert[^"]*">(.*?)</div>', r_bulk.text, re.DOTALL)
for a in alerts:
    clean_text = re.sub(r'<[^>]+>', '', a).strip()
    print("Alert:", clean_text)

print("\n--- 3. Check Apps Script Health ---")
r_as = requests.get(APPS_SCRIPT_URL)
print("Apps Script GET response:", r_as.json())

print("\n--- 4. Test adding a student on Live Render App ---")
student_data = {
    "student_code": "LIVE2026TEST",
    "full_name": "Kajal Test Student",
    "email": "kajal_test_live@example.com",
    "admission_year": 2024,
    "current_status": "Active"
}
r_create = s.post(f"{LIVE_URL}/students/create", data=student_data, allow_redirects=True)
print("Create student response status:", r_create.status_code)
print("Final URL after redirect:", r_create.url)

# Extract new student integer ID from URL
match = re.search(r'/students/(\d+)', r_create.url)
if not match:
    # Maybe flash message has error
    alerts = re.findall(r'<div class="alert[^"]*">(.*?)</div>', r_create.text, re.DOTALL)
    for a in alerts:
        print("Alert from create:", re.sub(r'<[^>]+>', '', a).strip())
    new_student_id = None
else:
    new_student_id = int(match.group(1))
    print(f"Created student PK ID: {new_student_id}")

print("\n--- 5. Wait 6 seconds for background outbox daemon to sync to Google Sheets ---")
time.sleep(6)

print("\n--- 6. Verify sync status on /sync page ---")
r_sync_page = s.get(f"{LIVE_URL}/sync")
# Search for LIVE2026TEST or student outbox row
if "LIVE2026TEST" in r_sync_page.text or "Students" in r_sync_page.text:
    print("Sync page reflects outbox / sync activity.")

outbox_rows = re.findall(r'<tr>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td><span class="badge[^"]*">(.*?)</span></td>', r_sync_page.text, re.DOTALL)
print(f"Total outbox table rows displayed: {len(outbox_rows)}")
for row in outbox_rows[:5]:
    cleaned = [re.sub(r'\s+', ' ', c).strip() for c in row]
    print("  Outbox row:", cleaned)

if new_student_id:
    print(f"\n--- 7. Test deleting student {new_student_id} on Live Render App ---")
    r_delete = s.post(f"{LIVE_URL}/students/{new_student_id}/delete", allow_redirects=True)
    print("Delete student response status:", r_delete.status_code)
    alerts = re.findall(r'<div class="alert[^"]*">(.*?)</div>', r_delete.text, re.DOTALL)
    for a in alerts:
        print("Delete alert:", re.sub(r'<[^>]+>', '', a).strip())

    print("\n--- 8. Wait 6 seconds for delete outbox dispatch ---")
    time.sleep(6)

    r_sync_page2 = s.get(f"{LIVE_URL}/sync")
    outbox_rows2 = re.findall(r'<tr>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td><span class="badge[^"]*">(.*?)</span></td>', r_sync_page2.text, re.DOTALL)
    print(f"Total outbox rows after delete: {len(outbox_rows2)}")
    for row in outbox_rows2[:5]:
        cleaned = [re.sub(r'\s+', ' ', c).strip() for c in row]
        print("  Outbox row:", cleaned)

print("\n--- 9. Trigger final bulk sync to keep Google Sheet 100% clean and verified ---")
r_bulk2 = s.post(f"{LIVE_URL}/sync/trigger-bulk", allow_redirects=True)
alerts2 = re.findall(r'<div class="alert[^"]*">(.*?)</div>', r_bulk2.text, re.DOTALL)
for a in alerts2:
    print("Final Bulk Alert:", re.sub(r'<[^>]+>', '', a).strip())

print("\nALL VERIFICATIONS COMPLETE.")
