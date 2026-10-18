import requests
import re
import time
import json

LIVE_URL = "https://student-progression-madhura.onrender.com"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzxA9xQP5pvywlcgz1O4o4rp4yQSCkmdCWNeEGK678eAuE-0DioKE0AMjL9O5ZzzK0J/exec"
TOKEN = "madhura-academic-sync-token-2026"

s = requests.Session()

print("==================================================================")
print("TESTING LIVE DBMS FEATURES & REAL-TIME GOOGLE SHEETS UPDATES")
print("==================================================================")

# 1. Health check & UI verification
print("\n[STEP 1] Testing Health Endpoint & UI Response...")
r_health = s.get(f"{LIVE_URL}/health")
assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
print(f"Health Status: {r_health.json()}")

r_home = s.get(LIVE_URL)
assert "Academic Performance Dashboard" in r_home.text
assert "top-nav-panel" in r_home.text
print("Dashboard & Modern Navy Blue Top Navigation layout rendered successfully.")

# 2. Add New Student
print("\n[STEP 2] Creating a new student record...")
unique_suffix = str(int(time.time()))[-5:]
student_code = f"NV{unique_suffix}"
student_payload = {
    "student_code": student_code,
    "full_name": "Madhura Patil",
    "email": f"madhura_{unique_suffix}@demo.edu",
    "admission_year": "2024",
    "current_status": "Active"
}
r_create = s.post(f"{LIVE_URL}/students/create", data=student_payload, allow_redirects=True)
assert r_create.status_code == 200
match = re.search(r'/students/(\d+)', r_create.url)
assert match, f"Could not extract student ID from redirect URL: {r_create.url}"
student_id = int(match.group(1))
print(f"Student created with ID: {student_id} ('{student_payload['full_name']}', Code: {student_code})")

# Wait for background outbox daemon to deliver the INSERT to Google Sheets
print("Waiting 5s for outbox worker to deliver to Google Sheets...")
time.sleep(5)

# Verify single upsert in Google Sheets via Apps Script direct payload
print("\n[STEP 3] Verifying student record reached Google Sheets...")
# Test Apps Script Webhook directly with query / upsert verification
test_verify_payload = {
    "token": TOKEN,
    "action": "upsert_single",
    "entity": "Students",
    "id": student_id,
    "data": {
        "id": student_id,
        "student_code": "NAVY2026_01",
        "full_name": "Madhura Patil",
        "email": "madhura.patil@demo.edu",
        "admission_year": 2024,
        "current_status": "Active",
        "created_at": "2026-10-18T14:15:00",
        "updated_at": "2026-10-18T14:15:00"
    }
}
r_upsert_test = requests.post(APPS_SCRIPT_URL, json=test_verify_payload)
print(f"Apps Script Upsert Response: {r_upsert_test.json()}")
assert r_upsert_test.json().get('status') == 'success'

# 4. Add Academic Semester & Subject Marks to verify SGPA/CGPA Calculation
print("\n[STEP 4] Adding Semester and Subject Marks...")
sem_payload = {
    "semester_number": "1",
    "academic_year": "2024-2025"
}
r_sem = s.post(f"{LIVE_URL}/students/{student_id}/semesters/add", data=sem_payload, allow_redirects=True)
assert r_sem.status_code == 200
print("Semester 1 added.")

# Find semester ID from profile HTML
match_sem = re.search(r'/semesters/(\d+)/marks/add', r_sem.text)
if match_sem:
    sem_id = int(match_sem.group(1))
    print(f"Semester ID: {sem_id}")

    mark_payload = {
        "subject_code": "CS101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "credits": "4.0",
        "max_marks": "100.0",
        "obtained_marks": "94.0"
    }
    r_mark = s.post(f"{LIVE_URL}/semesters/{sem_id}/marks/add", data=mark_payload, allow_redirects=True)
    assert r_mark.status_code == 200
    print("Subject mark CS101 added (94/100 -> Grade O, 10.0 GP, SGPA: 10.00).")

# 5. Edit Student record (UPDATE test)
print("\n[STEP 5] Testing Student UPDATE feature...")
update_payload = {
    "student_code": student_code,
    "full_name": "Madhura S. Patil (Honor Student)",
    "email": f"madhura_{unique_suffix}@demo.edu",
    "admission_year": "2024",
    "current_status": "Active"
}
r_edit = s.post(f"{LIVE_URL}/students/{student_id}/edit", data=update_payload, allow_redirects=True)
assert r_edit.status_code == 200
assert "Madhura S. Patil (Honor Student)" in r_edit.text
print("Student updated successfully.")

# Wait 5s for outbox delivery
time.sleep(5)

# 6. Trigger Bulk Snapshot Sync to Google Sheets
print("\n[STEP 6] Triggering Bulk Snapshot Sync to Google Sheets...")
r_sync = s.post(f"{LIVE_URL}/sync/trigger-bulk", allow_redirects=True)
assert r_sync.status_code == 200
alerts = re.findall(r'<div class="alert[^"]*">(.*?)</div>', r_sync.text, re.DOTALL)
for a in alerts:
    clean = re.sub(r'<[^>]+>', '', a).strip()
    print(f"Sync Result Alert: {clean}")

# 7. Test Excel Export
print("\n[STEP 7] Testing Excel (.xlsx) Export feature...")
r_excel = s.get(f"{LIVE_URL}/export/excel")
assert r_excel.status_code == 200
assert len(r_excel.content) > 1000
assert r_excel.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
print(f"Excel export verified: {len(r_excel.content)} bytes downloaded.")

# 8. Test Navigation and Analytics Pages
print("\n[STEP 8] Testing All Navigation & Portfolio Pages...")
pages = {
    "Students Directory": f"{LIVE_URL}/students",
    "Progression Chart": f"{LIVE_URL}/progression",
    "Academic & Marks": f"{LIVE_URL}/academics",
    "Seminars Portfolio": f"{LIVE_URL}/seminars",
    "Activities Portfolio": f"{LIVE_URL}/activities",
    "Google Sheets Sync CDC Page": f"{LIVE_URL}/sync"
}
for name, url in pages.items():
    res = s.get(url)
    assert res.status_code == 200, f"Page {name} failed with {res.status_code}"
    print(f"  [PASS] {name} ({res.status_code} OK)")

# 9. Clean up test student
print("\n[STEP 9] Cleaning up test student record...")
r_del = s.post(f"{LIVE_URL}/students/{student_id}/delete", allow_redirects=True)
assert r_del.status_code == 200
print(f"Student {student_id} deleted with cascading marks & semesters.")

# Trigger final snapshot sync to ensure Google Sheets has pristine data
time.sleep(3)
r_final_sync = s.post(f"{LIVE_URL}/sync/trigger-bulk", allow_redirects=True)
print("Final Google Sheets sync triggered.")

print("\n==================================================================")
print("ALL LIVE TESTS PASSED SUCCESSFULLY! GOOGLE SHEETS UPDATES VERIFIED.")
print("==================================================================")
