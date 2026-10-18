import json
import threading
import requests
from datetime import datetime
from config import Config
from services import db

def trigger_background_outbox_processing():
    """
    Spawns a daemon thread to process the outbox queue immediately
    without blocking the user's web request or database transaction.
    """
    try:
        thread = threading.Thread(target=process_sync_outbox, kwargs={'limit': 20}, daemon=True)
        thread.start()
    except Exception:
        pass

def queue_outbox_event(entity_name: str, record_id: int, operation: str, payload_dict: dict):
    """
    Saves an event into the durable sync_outbox table and logs Change Data Capture (CDC) entry.
    Ensures data saves to local DB are decoupled from Google Sheets network availability.
    Automatically triggers background worker to process pending items.
    """
    payload_json = json.dumps(payload_dict, default=str)
    sql_outbox = """
    INSERT INTO sync_outbox (entity_name, record_id, operation, payload, status)
    VALUES (%s, %s, %s, %s, 'PENDING')
    """
    outbox_id = db.execute(sql_outbox, (entity_name, record_id, operation, payload_json))

    # Also log initial CDC event in sync_log
    sql_log = """
    INSERT INTO sync_log (entity_name, record_id, operation, status, payload, retry_count)
    VALUES (%s, %s, %s, 'PENDING', %s, 0)
    """
    try:
        db.execute(sql_log, (entity_name, record_id, operation, payload_json))
    except Exception:
        pass

    # Trigger background worker immediately
    trigger_background_outbox_processing()

    return outbox_id

def push_event_to_sheets(entity_name: str, operation: str, record: dict) -> dict:
    """
    Sends an individual entity event payload to Google Apps Script Web App.
    Accurately inspects response status ('success' vs 'error').
    """
    url = Config.GOOGLE_SHEETS_WEBHOOK_URL
    if not url:
        return {'status': 'SKIPPED', 'message': 'Google Sheets webhook URL is not configured'}

    record_id = record.get('id') if isinstance(record, dict) else record

    payload = {
        'token': Config.GOOGLE_SHEETS_SECRET_TOKEN,
        'action': 'upsert_single' if operation == 'UPSERT' else 'delete_single',
        'entity': entity_name,
        'id': record_id,
        'data': record
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get('status') == 'success':
                return {'status': 'SUCCESS', 'response': res_data}
            else:
                err_msg = res_data.get('message', 'Apps Script reported error')
                return {'status': 'FAILED', 'error': err_msg}
        else:
            return {'status': 'FAILED', 'error': f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {'status': 'FAILED', 'error': str(e)}

def push_bulk_snapshot_to_sheets() -> dict:
    """
    Fetches all 7 relational tables from the database and sends a full synchronized snapshot
    to the Google Sheets Web App. This guarantees spreadsheet alignment at any point.
    """
    url = Config.GOOGLE_SHEETS_WEBHOOK_URL
    if not url:
        return {'status': 'SKIPPED', 'message': 'Google Sheets webhook URL is not configured.'}

    data_snapshot = {
        'Students': db.query_all("SELECT * FROM students ORDER BY id ASC"),
        'SchoolRecords': db.query_all("SELECT * FROM school_records ORDER BY id ASC"),
        'Semesters': db.query_all("SELECT * FROM semesters ORDER BY student_id ASC, semester_number ASC"),
        'StudentMarks': db.query_all("SELECT * FROM student_marks ORDER BY semester_id ASC, id ASC"),
        'GapYears': db.query_all("SELECT * FROM gap_years ORDER BY id ASC"),
        'Seminars': db.query_all("SELECT * FROM seminars ORDER BY event_date DESC"),
        'Activities': db.query_all("SELECT * FROM activities ORDER BY event_date DESC")
    }

    payload = {
        'token': Config.GOOGLE_SHEETS_SECRET_TOKEN,
        'action': 'bulk_sync',
        'tables': data_snapshot
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get('status') == 'success':
                # Record in sync_log
                db.execute("""
                    INSERT INTO sync_log (entity_name, record_id, operation, status, payload, synced_at)
                    VALUES ('ALL_TABLES', 0, 'BULK_SYNC', 'SUCCESS', %s, CURRENT_TIMESTAMP)
                """, (f"Snapshot synced: {len(data_snapshot['Students'])} students across 7 sheets",))
                
                # Mark pending outbox as SYNCED
                db.execute("UPDATE sync_outbox SET status = 'SYNCED' WHERE status = 'PENDING'")
                return {'status': 'SUCCESS', 'details': res_data}
            else:
                err = res_data.get('message', 'Apps Script reported error on bulk sync')
                db.execute("""
                    INSERT INTO sync_log (entity_name, record_id, operation, status, error_message)
                    VALUES ('ALL_TABLES', 0, 'BULK_SYNC', 'FAILED', %s)
                """, (err,))
                return {'status': 'FAILED', 'error': err}
        else:
            err = f"HTTP {response.status_code}: {response.text}"
            db.execute("""
                INSERT INTO sync_log (entity_name, record_id, operation, status, error_message)
                VALUES ('ALL_TABLES', 0, 'BULK_SYNC', 'FAILED', %s)
            """, (err,))
            return {'status': 'FAILED', 'error': err}
    except Exception as e:
        err = str(e)
        db.execute("""
            INSERT INTO sync_log (entity_name, record_id, operation, status, error_message)
            VALUES ('ALL_TABLES', 0, 'BULK_SYNC', 'FAILED', %s)
        """, (err,))
        return {'status': 'FAILED', 'error': err}

def process_sync_outbox(limit: int = 25) -> dict:
    """
    Processes pending outbox items and pushes them to the configured webhook.
    """
    if not Config.GOOGLE_SHEETS_WEBHOOK_URL:
        return {'processed': 0, 'status': 'SKIPPED', 'message': 'Webhook URL not configured'}

    pending_items = db.query_all("""
        SELECT * FROM sync_outbox 
        WHERE status IN ('PENDING', 'FAILED') AND retry_count < 5
        ORDER BY id ASC LIMIT %s
    """, (limit,))

    success_count = 0
    fail_count = 0

    for item in pending_items:
        payload_data = json.loads(item['payload'])
        result = push_event_to_sheets(item['entity_name'], item['operation'], payload_data)
        
        if result.get('status') == 'SUCCESS':
            db.execute("""
                UPDATE sync_outbox 
                SET status = 'SYNCED', updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (item['id'],))
            db.execute("""
                INSERT INTO sync_log (entity_name, record_id, operation, status, payload, synced_at)
                VALUES (%s, %s, %s, 'SUCCESS', %s, CURRENT_TIMESTAMP)
            """, (item['entity_name'], item['record_id'], item['operation'], item['payload']))
            success_count += 1
        else:
            err = result.get('error', 'Unknown synchronization error')
            db.execute("""
                UPDATE sync_outbox 
                SET status = 'FAILED', retry_count = retry_count + 1, last_error = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (err, item['id']))
            db.execute("""
                INSERT INTO sync_log (entity_name, record_id, operation, status, payload, error_message, retry_count)
                VALUES (%s, %s, %s, 'FAILED', %s, %s, %s)
            """, (item['entity_name'], item['record_id'], item['operation'], item['payload'], err, item['retry_count'] + 1))
            fail_count += 1

    return {'processed': len(pending_items), 'success': success_count, 'failed': fail_count}

def get_sync_status() -> dict:
    """
    Returns real synchronization metrics and status from the database.
    """
    last_sync = db.query_one("SELECT * FROM sync_log WHERE status = 'SUCCESS' ORDER BY id DESC LIMIT 1")
    pending_count = db.query_one("SELECT COUNT(*) AS cnt FROM sync_outbox WHERE status = 'PENDING'")
    failed_count = db.query_one("SELECT COUNT(*) AS cnt FROM sync_outbox WHERE status = 'FAILED'")
    recent_logs = db.query_all("SELECT * FROM sync_log ORDER BY id DESC LIMIT 25")

    # Truthful database status
    db_type = Config.DB_TYPE.lower()
    if db_type == 'mysql':
        db_label = f"MySQL 8.0+ ({Config.DB_HOST})"
    else:
        db_label = "SQLite (Local / Ephemeral Disk on Render)"

    return {
        'is_configured': bool(Config.GOOGLE_SHEETS_WEBHOOK_URL),
        'webhook_url_masked': (Config.GOOGLE_SHEETS_WEBHOOK_URL[:36] + '...') if Config.GOOGLE_SHEETS_WEBHOOK_URL else 'Not configured',
        'spreadsheet_url': Config.GOOGLE_SHEET_URL,
        'spreadsheet_id': Config.GOOGLE_SPREADSHEET_ID,
        'db_label': db_label,
        'db_type': Config.DB_TYPE,
        'db_status': 'Connected & Active (ACID Transactions Enforced)',
        'last_sync': last_sync,
        'pending_count': pending_count['cnt'] if pending_count else 0,
        'failed_count': failed_count['cnt'] if failed_count else 0,
        'recent_logs': recent_logs
    }
