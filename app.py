import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from config import Config
from services import db, calculations, google_sheets, export_excel

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database is initialized on startup
with app.app_context():
    try:
        db.init_db(seed_if_empty=True)
    except Exception as e:
        app.logger.error(f"Database initialization notice: {e}")

@app.context_processor
def inject_global_settings():
    db_type = Config.DB_TYPE.lower()
    if db_type == 'mysql':
        db_badge = f"MySQL 8.0+ ({Config.DB_HOST})"
    else:
        db_badge = "SQLite (Local / Ephemeral Disk)"
    return {
        'current_db_badge': db_badge,
        'current_db_type': Config.DB_TYPE,
        'google_sheet_url': Config.GOOGLE_SHEET_URL,
        'google_spreadsheet_id': Config.GOOGLE_SPREADSHEET_ID
    }

# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------
@app.route('/health')
def health_check():
    """Health check endpoint for Render and deployment uptime monitoring."""
    try:
        # Check DB connection
        test_row = db.query_one("SELECT 1 AS alive")
        db_alive = bool(test_row and test_row.get('alive') == 1)
    except Exception as e:
        db_alive = False

    return jsonify({
        'status': 'healthy' if db_alive else 'degraded',
        'database': 'connected' if db_alive else 'disconnected',
        'db_type': Config.DB_TYPE,
        'sheets_configured': bool(Config.GOOGLE_SHEETS_WEBHOOK_URL),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), (200 if db_alive else 503)

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
@app.route('/')
def dashboard():
    """System Dashboard: High-level academic analytics, KPIs, and charts."""
    # Summary stats
    stats_query = """
    SELECT 
        COUNT(*) AS total_students,
        SUM(CASE WHEN current_status = 'Active' THEN 1 ELSE 0 END) AS active_students,
        SUM(CASE WHEN current_status = 'On Leave' THEN 1 ELSE 0 END) AS on_leave_students,
        SUM(CASE WHEN current_status = 'Graduated' THEN 1 ELSE 0 END) AS graduated_students
    FROM students
    """
    stats = db.query_one(stats_query) or {'total_students': 0, 'active_students': 0, 'on_leave_students': 0, 'graduated_students': 0}

    # Department Average CGPA and Max CGPA calculation
    # Rule: Average of the latest CGPA recorded across all students
    cgpa_query = """
    SELECT 
        ROUND(AVG(latest.cgpa), 2) AS avg_cgpa,
        MAX(latest.cgpa) AS max_cgpa
    FROM (
        SELECT s.id, s.cgpa
        FROM semesters s
        INNER JOIN (
            SELECT student_id, MAX(semester_number) AS max_sem
            FROM semesters
            GROUP BY student_id
        ) m ON s.student_id = m.student_id AND s.semester_number = m.max_sem
    ) latest
    """
    cgpa_stats = db.query_one(cgpa_query) or {'avg_cgpa': 0.00, 'max_cgpa': 0.00}

    # Progression chart data: Average SGPA across Semesters 1 to 8
    sem_progression = db.query_all("""
        SELECT semester_number, ROUND(AVG(sgpa), 2) AS avg_sgpa, COUNT(*) AS student_count
        FROM semesters
        GROUP BY semester_number
        ORDER BY semester_number ASC
    """)

    # Activities category distribution
    activity_dist = db.query_all("""
        SELECT category, COUNT(*) AS count
        FROM activities
        GROUP BY category
    """)

    # Recent Seminars & Activities for feed
    recent_seminars = db.query_all("""
        SELECT sem.*, s.full_name, s.student_code
        FROM seminars sem
        JOIN students s ON sem.student_id = s.id
        ORDER BY sem.event_date DESC LIMIT 5
    """)

    recent_activities = db.query_all("""
        SELECT act.*, s.full_name, s.student_code
        FROM activities act
        JOIN students s ON act.student_id = s.id
        ORDER BY act.event_date DESC LIMIT 5
    """)

    return render_template(
        'dashboard.html',
        stats=stats,
        cgpa_stats=cgpa_stats,
        sem_progression=sem_progression,
        activity_dist=activity_dist,
        recent_seminars=recent_seminars,
        recent_activities=recent_activities
    )

# -----------------------------------------------------------------------------
# Student Directory & CRUD
# -----------------------------------------------------------------------------
@app.route('/students')
def student_directory():
    """Student Directory with search, admission year, and status filters."""
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    year_filter = request.args.get('year', '').strip()

    query = """
    SELECT 
        s.*,
        (SELECT MAX(sem.cgpa) FROM semesters sem WHERE sem.student_id = s.id AND sem.semester_number = (
            SELECT MAX(s2.semester_number) FROM semesters s2 WHERE s2.student_id = s.id
        )) AS latest_cgpa,
        (SELECT COUNT(*) FROM semesters sem WHERE sem.student_id = s.id) AS total_semesters
    FROM students s
    WHERE 1=1
    """
    params = []

    if search:
        query += " AND (s.full_name LIKE %s OR s.student_code LIKE %s OR s.email LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    if status_filter:
        query += " AND s.current_status = %s"
        params.append(status_filter)

    if year_filter and year_filter.isdigit():
        query += " AND s.admission_year = %s"
        params.append(int(year_filter))

    query += " ORDER BY s.id DESC"
    students = db.query_all(query, tuple(params))

    # Distinct years for dropdown filter
    years = db.query_all("SELECT DISTINCT admission_year FROM students ORDER BY admission_year DESC")

    return render_template(
        'students.html',
        students=students,
        search=search,
        status_filter=status_filter,
        year_filter=year_filter,
        years=years
    )

@app.route('/students/create', methods=['POST'])
def student_create():
    """Create a new student record with server-side validation and outbox queue."""
    student_code = request.form.get('student_code', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    admission_year = request.form.get('admission_year', '').strip()
    current_status = request.form.get('current_status', 'Active').strip()

    if not student_code or not full_name or not email or not admission_year:
        flash('All fields are required.', 'error')
        return redirect(url_for('student_directory'))

    # Check for uniqueness
    existing = db.query_one("SELECT id FROM students WHERE student_code = %s OR email = %s", (student_code, email))
    if existing:
        flash('A student with this Student Code or Email already exists.', 'error')
        return redirect(url_for('student_directory'))

    try:
        new_id = db.execute("""
            INSERT INTO students (student_code, full_name, email, admission_year, current_status)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_code, full_name, email, int(admission_year), current_status))

        # Queue outbox event
        google_sheets.queue_outbox_event('Students', new_id, 'UPSERT', {
            'id': new_id,
            'student_code': student_code,
            'full_name': full_name,
            'email': email,
            'admission_year': int(admission_year),
            'current_status': current_status
        })

        flash(f'Student "{full_name}" registered successfully.', 'success')
        return redirect(url_for('student_profile', student_id=new_id))
    except Exception as e:
        flash(f'Error registering student: {str(e)}', 'error')
        return redirect(url_for('student_directory'))

@app.route('/students/<int:student_id>')
def student_profile(student_id):
    """Complete 360-degree Student Academic Portfolio and Progress Profile."""
    student = db.query_one("SELECT * FROM students WHERE id = %s", (student_id,))
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('student_directory'))

    # School records (10th, 12th)
    school_records = db.query_all("SELECT * FROM school_records WHERE student_id = %s ORDER BY passing_year ASC", (student_id,))

    # Semesters & Marks
    semesters = db.query_all("SELECT * FROM semesters WHERE student_id = %s ORDER BY semester_number ASC", (student_id,))
    
    # Fetch marks for each semester
    sem_ids = [s['id'] for s in semesters]
    marks_by_sem = {}
    if sem_ids:
        placeholders = ', '.join(['%s'] * len(sem_ids))
        all_marks = db.query_all(f"SELECT * FROM student_marks WHERE semester_id IN ({placeholders}) ORDER BY subject_code ASC", tuple(sem_ids))
        for m in all_marks:
            marks_by_sem.setdefault(m['semester_id'], []).append(m)

    for sem in semesters:
        sem['marks'] = marks_by_sem.get(sem['id'], [])

    # Gap years
    gap_years = db.query_all("SELECT * FROM gap_years WHERE student_id = %s ORDER BY start_year ASC", (student_id,))

    # Seminars
    seminars = db.query_all("SELECT * FROM seminars WHERE student_id = %s ORDER BY event_date DESC", (student_id,))

    # Activities
    activities = db.query_all("SELECT * FROM activities WHERE student_id = %s ORDER BY event_date DESC", (student_id,))

    # Progression chart data for this student
    progression_labels = [f"Sem {s['semester_number']}" for s in semesters]
    progression_sgpa = [float(s['sgpa']) for s in semesters]
    progression_cgpa = [float(s['cgpa']) for s in semesters]

    return render_template(
        'student_profile.html',
        student=student,
        school_records=school_records,
        semesters=semesters,
        gap_years=gap_years,
        seminars=seminars,
        activities=activities,
        progression_labels=json.dumps(progression_labels),
        progression_sgpa=json.dumps(progression_sgpa),
        progression_cgpa=json.dumps(progression_cgpa),
        grading_system=Config.GRADING_SYSTEM
    )

@app.route('/students/<int:student_id>/edit', methods=['POST'])
def student_edit(student_id):
    """Update student basic information."""
    student_code = request.form.get('student_code', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    admission_year = request.form.get('admission_year', '').strip()
    current_status = request.form.get('current_status', 'Active').strip()

    try:
        db.execute("""
            UPDATE students 
            SET student_code = %s, full_name = %s, email = %s, admission_year = %s, current_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (student_code, full_name, email, int(admission_year), current_status, student_id))

        google_sheets.queue_outbox_event('Students', student_id, 'UPSERT', {
            'id': student_id,
            'student_code': student_code,
            'full_name': full_name,
            'email': email,
            'admission_year': int(admission_year),
            'current_status': current_status
        })

        flash('Student profile updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating student: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/students/<int:student_id>/delete', methods=['POST'])
def student_delete(student_id):
    """Delete a student and cascade all associated records."""
    try:
        db.execute("DELETE FROM students WHERE id = %s", (student_id,))
        google_sheets.queue_outbox_event('Students', student_id, 'DELETE', {'id': student_id})
        flash('Student and all associated records deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')

    return redirect(url_for('student_directory'))

# -----------------------------------------------------------------------------
# Academic Records: Semesters and Marks Management
# -----------------------------------------------------------------------------
@app.route('/students/<int:student_id>/semesters/add', methods=['POST'])
def semester_add(student_id):
    """Add a new semester for a student and initialize recalculation."""
    semester_number = request.form.get('semester_number', '').strip()
    academic_year = request.form.get('academic_year', '').strip()

    if not semester_number or not academic_year:
        flash('Semester number and academic year are required.', 'error')
        return redirect(url_for('student_profile', student_id=student_id))

    existing = db.query_one("SELECT id FROM semesters WHERE student_id = %s AND semester_number = %s", (student_id, int(semester_number)))
    if existing:
        flash(f'Semester {semester_number} already exists for this student.', 'error')
        return redirect(url_for('student_profile', student_id=student_id))

    try:
        sem_id = db.execute("""
            INSERT INTO semesters (student_id, semester_number, academic_year, credits, sgpa, cgpa)
            VALUES (%s, %s, %s, 0.0, 0.00, 0.00)
        """, (student_id, int(semester_number), academic_year))

        # Recalculate CGPA chain
        _sync_recalculate_student_academics(student_id)

        google_sheets.queue_outbox_event('Semesters', sem_id, 'UPSERT', {
            'id': sem_id,
            'student_id': student_id,
            'semester_number': int(semester_number),
            'academic_year': academic_year,
            'credits': 0.0,
            'sgpa': 0.00,
            'cgpa': 0.00
        })

        flash(f'Semester {semester_number} added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding semester: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/semesters/<int:semester_id>/delete', methods=['POST'])
def semester_delete(semester_id):
    """Delete a semester and recalculate subsequent academic progression."""
    sem = db.query_one("SELECT student_id FROM semesters WHERE id = %s", (semester_id,))
    if not sem:
        flash('Semester not found.', 'error')
        return redirect(url_for('student_directory'))

    student_id = sem['student_id']
    try:
        db.execute("DELETE FROM semesters WHERE id = %s", (semester_id,))
        _sync_recalculate_student_academics(student_id)
        google_sheets.queue_outbox_event('Semesters', semester_id, 'DELETE', {'id': semester_id})
        flash('Semester and related marks removed.', 'success')
    except Exception as e:
        flash(f'Error deleting semester: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/semesters/<int:semester_id>/marks/add', methods=['POST'])
def mark_add(semester_id):
    """Add a subject mark to a semester, update SGPA and CGPA cascade."""
    sem = db.query_one("SELECT student_id FROM semesters WHERE id = %s", (semester_id,))
    if not sem:
        flash('Semester record not found.', 'error')
        return redirect(url_for('student_directory'))

    student_id = sem['student_id']
    subject_code = request.form.get('subject_code', '').strip().upper()
    subject_name = request.form.get('subject_name', '').strip()
    credits = float(request.form.get('credits', 4.0))
    obtained_marks = float(request.form.get('obtained_marks', 0.0))
    max_marks = float(request.form.get('max_marks', 100.0))

    if obtained_marks > max_marks or obtained_marks < 0:
        flash('Obtained marks cannot exceed maximum marks or be negative.', 'error')
        return redirect(url_for('student_profile', student_id=student_id))

    grade, _ = calculations.get_grade_and_point(obtained_marks, max_marks)

    try:
        mark_id = db.execute("""
            INSERT INTO student_marks (semester_id, subject_code, subject_name, credits, max_marks, obtained_marks, grade)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (semester_id, subject_code, subject_name, credits, max_marks, obtained_marks, grade))

        # Recalculate semester SGPA and student CGPA
        _recalculate_semester_and_cgpa(semester_id, student_id)

        google_sheets.queue_outbox_event('StudentMarks', mark_id, 'UPSERT', {
            'id': mark_id,
            'semester_id': semester_id,
            'subject_code': subject_code,
            'subject_name': subject_name,
            'credits': credits,
            'max_marks': max_marks,
            'obtained_marks': obtained_marks,
            'grade': grade
        })

        flash(f'Mark for {subject_name} ({subject_code}) added with Grade {grade}.', 'success')
    except Exception as e:
        flash(f'Error adding subject mark: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/marks/<int:mark_id>/delete', methods=['POST'])
def mark_delete(mark_id):
    """Delete a subject mark and automatically recalculate affected SGPA/CGPA."""
    mark = db.query_one("""
        SELECT m.semester_id, s.student_id 
        FROM student_marks m
        JOIN semesters s ON m.semester_id = s.id
        WHERE m.id = %s
    """, (mark_id,))
    if not mark:
        flash('Mark record not found.', 'error')
        return redirect(url_for('student_directory'))

    semester_id = mark['semester_id']
    student_id = mark['student_id']

    try:
        db.execute("DELETE FROM student_marks WHERE id = %s", (mark_id,))
        _recalculate_semester_and_cgpa(semester_id, student_id)
        google_sheets.queue_outbox_event('StudentMarks', mark_id, 'DELETE', {'id': mark_id})
        flash('Subject mark removed and academic metrics recalculated.', 'success')
    except Exception as e:
        flash(f'Error deleting mark: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

def _recalculate_semester_and_cgpa(semester_id: int, student_id: int):
    """Calculates updated SGPA for the semester, saves it, and recalculates cumulative CGPA."""
    marks = db.query_all("SELECT credits, obtained_marks, max_marks, grade FROM student_marks WHERE semester_id = %s", (semester_id,))
    total_credits, sgpa = calculations.calculate_sgpa(marks)
    
    db.execute("""
        UPDATE semesters 
        SET credits = %s, sgpa = %s
        WHERE id = %s
    """, (total_credits, sgpa, semester_id))

    _sync_recalculate_student_academics(student_id)

def _sync_recalculate_student_academics(student_id: int):
    """Recalculates cumulative CGPA across all ordered semesters for a student."""
    sems = db.query_all("SELECT id, semester_number, credits, sgpa FROM semesters WHERE student_id = %s ORDER BY semester_number ASC", (student_id,))
    updated_sems = calculations.recalculate_student_cgpa(sems)

    for s in updated_sems:
        db.execute("UPDATE semesters SET cgpa = %s WHERE id = %s", (s['cgpa'], s['id']))
        # Queue outbox update for semester
        google_sheets.queue_outbox_event('Semesters', s['id'], 'UPSERT', s)

# -----------------------------------------------------------------------------
# School Records (10th / 12th)
# -----------------------------------------------------------------------------
@app.route('/students/<int:student_id>/school-records/add', methods=['POST'])
def school_record_add(student_id):
    """Add a 10th/12th school record with auto-calculated percentage."""
    education_level = request.form.get('education_level', '').strip()
    institution = request.form.get('institution', '').strip()
    board = request.form.get('board', '').strip()
    passing_year = int(request.form.get('passing_year', 2022))
    max_marks = float(request.form.get('max_marks', 500.0))
    obtained_marks = float(request.form.get('obtained_marks', 0.0))

    pct = calculations.calculate_percentage(obtained_marks, max_marks)

    try:
        rec_id = db.execute("""
            INSERT INTO school_records (student_id, education_level, institution, board, passing_year, max_marks, obtained_marks, percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (student_id, education_level, institution, board, passing_year, max_marks, obtained_marks, pct))

        google_sheets.queue_outbox_event('SchoolRecords', rec_id, 'UPSERT', {
            'id': rec_id,
            'student_id': student_id,
            'education_level': education_level,
            'institution': institution,
            'board': board,
            'passing_year': passing_year,
            'max_marks': max_marks,
            'obtained_marks': obtained_marks,
            'percentage': pct
        })

        flash(f'School record for {education_level} added successfully ({pct}%).', 'success')
    except Exception as e:
        flash(f'Error adding school record: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/school-records/<int:record_id>/delete', methods=['POST'])
def school_record_delete(record_id):
    rec = db.query_one("SELECT student_id FROM school_records WHERE id = %s", (record_id,))
    if rec:
        db.execute("DELETE FROM school_records WHERE id = %s", (record_id,))
        google_sheets.queue_outbox_event('SchoolRecords', record_id, 'DELETE', {'id': record_id})
        flash('School record deleted.', 'success')
        return redirect(url_for('student_profile', student_id=rec['student_id']))
    return redirect(url_for('student_directory'))

# -----------------------------------------------------------------------------
# Gap Years
# -----------------------------------------------------------------------------
@app.route('/students/<int:student_id>/gap-years/add', methods=['POST'])
def gap_year_add(student_id):
    start_year = int(request.form.get('start_year', 2020))
    end_year = int(request.form.get('end_year', 2021))
    reason = request.form.get('reason', '').strip()
    remarks = request.form.get('remarks', '').strip()

    try:
        gid = db.execute("""
            INSERT INTO gap_years (student_id, start_year, end_year, reason, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, start_year, end_year, reason, remarks))

        google_sheets.queue_outbox_event('GapYears', gid, 'UPSERT', {
            'id': gid,
            'student_id': student_id,
            'start_year': start_year,
            'end_year': end_year,
            'reason': reason,
            'remarks': remarks
        })

        flash('Gap year record added.', 'success')
    except Exception as e:
        flash(f'Error adding gap year: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/gap-years/<int:gap_id>/delete', methods=['POST'])
def gap_year_delete(gap_id):
    gy = db.query_one("SELECT student_id FROM gap_years WHERE id = %s", (gap_id,))
    if gy:
        db.execute("DELETE FROM gap_years WHERE id = %s", (gap_id,))
        google_sheets.queue_outbox_event('GapYears', gap_id, 'DELETE', {'id': gap_id})
        flash('Gap year record removed.', 'success')
        return redirect(url_for('student_profile', student_id=gy['student_id']))
    return redirect(url_for('student_directory'))

# -----------------------------------------------------------------------------
# Progression Chart Page
# -----------------------------------------------------------------------------
@app.route('/progression')
def progression_chart_page():
    """Dedicated Progression Analytics and Comparative Student Curve Page."""
    student_id = request.args.get('student_id', '').strip()

    # Department progression across all semesters 1 to 8
    sem_progression = db.query_all("""
        SELECT 
            semester_number,
            ROUND(AVG(sgpa), 2) AS avg_sgpa,
            MAX(sgpa) AS max_sgpa,
            MIN(sgpa) AS min_sgpa,
            COUNT(*) AS student_count
        FROM semesters
        GROUP BY semester_number
        ORDER BY semester_number ASC
    """)

    # Grade distribution breakdown across all subject marks
    grade_distribution = db.query_all("""
        SELECT grade, COUNT(*) AS count
        FROM student_marks
        GROUP BY grade
        ORDER BY 
            CASE grade
                WHEN 'O' THEN 1
                WHEN 'A+' THEN 2
                WHEN 'A' THEN 3
                WHEN 'B+' THEN 4
                WHEN 'B' THEN 5
                WHEN 'C' THEN 6
                WHEN 'P' THEN 7
                ELSE 8
            END
    """)

    # List of all students for the dropdown comparison
    all_students = db.query_all("SELECT id, full_name, student_code FROM students ORDER BY full_name ASC")

    # If specific student selected, get their progression curve
    selected_student = None
    student_sems = []
    if student_id and student_id.isdigit():
        selected_student = db.query_one("SELECT * FROM students WHERE id = %s", (int(student_id),))
        if selected_student:
            student_sems = db.query_all("SELECT semester_number, sgpa, cgpa, credits FROM semesters WHERE student_id = %s ORDER BY semester_number ASC", (int(student_id),))

    # Top performers (highest current CGPA)
    top_performers = db.query_all("""
        SELECT 
            s.id, s.full_name, s.student_code, s.admission_year,
            latest.cgpa, latest.max_sem
        FROM students s
        INNER JOIN (
            SELECT student_id, cgpa, semester_number AS max_sem
            FROM semesters s1
            WHERE semester_number = (
                SELECT MAX(s2.semester_number) FROM semesters s2 WHERE s2.student_id = s1.student_id
            )
        ) latest ON s.id = latest.student_id
        ORDER BY latest.cgpa DESC LIMIT 5
    """)

    return render_template(
        'progression.html',
        sem_progression=sem_progression,
        grade_distribution=grade_distribution,
        all_students=all_students,
        selected_student=selected_student,
        student_sems=student_sems,
        selected_student_id=student_id,
        top_performers=top_performers
    )

# -----------------------------------------------------------------------------
# Academic & Marks Page
# -----------------------------------------------------------------------------
@app.route('/academics')
def academics_page():
    """Master Academic Records, Semesters, and Subject Marks Overview."""
    student_id = request.args.get('student_id', '').strip()
    sem_num = request.args.get('semester', '').strip()

    query = """
        SELECT 
            sem.*,
            s.full_name,
            s.student_code,
            s.admission_year,
            (SELECT COUNT(*) FROM student_marks m WHERE m.semester_id = sem.id) AS subject_count
        FROM semesters sem
        JOIN students s ON sem.student_id = s.id
        WHERE 1=1
    """
    params = []
    if student_id and student_id.isdigit():
        query += " AND sem.student_id = %s"
        params.append(int(student_id))
    if sem_num and sem_num.isdigit():
        query += " AND sem.semester_number = %s"
        params.append(int(sem_num))

    query += " ORDER BY sem.student_id ASC, sem.semester_number ASC"
    semesters = db.query_all(query, tuple(params))

    # Summary metrics
    metrics = db.query_one("""
        SELECT 
            COUNT(DISTINCT student_id) AS active_students,
            COUNT(*) AS total_semesters,
            ROUND(AVG(sgpa), 2) AS avg_sgpa,
            ROUND(SUM(credits), 1) AS total_credits_earned
        FROM semesters
    """) or {'active_students': 0, 'total_semesters': 0, 'avg_sgpa': 0.0, 'total_credits_earned': 0.0}

    all_students = db.query_all("SELECT id, full_name, student_code FROM students ORDER BY full_name ASC")

    # Fetch marks for listed semesters
    sem_ids = [s['id'] for s in semesters]
    marks_by_sem = {}
    if sem_ids:
        placeholders = ', '.join(['%s'] * len(sem_ids))
        marks = db.query_all(f"SELECT * FROM student_marks WHERE semester_id IN ({placeholders}) ORDER BY subject_code ASC", tuple(sem_ids))
        for m in marks:
            marks_by_sem.setdefault(m['semester_id'], []).append(m)

    for sem in semesters:
        sem['marks'] = marks_by_sem.get(sem['id'], [])

    return render_template(
        'academics.html',
        semesters=semesters,
        metrics=metrics,
        all_students=all_students,
        current_student_id=student_id,
        current_sem_num=sem_num
    )

# -----------------------------------------------------------------------------
# Seminars Portfolio Page
# -----------------------------------------------------------------------------
@app.route('/seminars')
def seminars_page():
    """Dedicated Seminars & Conferences Portfolio with Search and Filters."""
    search = request.args.get('search', '').strip()
    part_type = request.args.get('type', '').strip()
    student_id = request.args.get('student_id', '').strip()

    query = """
        SELECT sem.*, s.full_name, s.student_code
        FROM seminars sem
        JOIN students s ON sem.student_id = s.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (sem.title LIKE %s OR sem.organizer LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])
    if part_type:
        query += " AND sem.participation_type = %s"
        params.append(part_type)
    if student_id and student_id.isdigit():
        query += " AND sem.student_id = %s"
        params.append(int(student_id))

    query += " ORDER BY sem.event_date DESC"
    seminars = db.query_all(query, tuple(params))

    # Stats
    stats = db.query_one("""
        SELECT 
            COUNT(*) AS total_seminars,
            SUM(CASE WHEN participation_type = 'Presenter' THEN 1 ELSE 0 END) AS presenters,
            SUM(CASE WHEN participation_type = 'Keynote' THEN 1 ELSE 0 END) AS keynotes,
            SUM(CASE WHEN participation_type = 'Attendee' THEN 1 ELSE 0 END) AS attendees
        FROM seminars
    """) or {'total_seminars': 0, 'presenters': 0, 'keynotes': 0, 'attendees': 0}

    all_students = db.query_all("SELECT id, full_name, student_code FROM students ORDER BY full_name ASC")

    return render_template(
        'seminars.html',
        seminars=seminars,
        stats=stats,
        all_students=all_students,
        search=search,
        current_type=part_type,
        current_student_id=student_id
    )

@app.route('/seminars/create', methods=['POST'])
def seminar_create_master():
    """Add seminar from master seminars directory."""
    student_id = request.form.get('student_id', '').strip()
    title = request.form.get('title', '').strip()
    organizer = request.form.get('organizer', '').strip()
    event_date = request.form.get('event_date', '').strip()
    participation_type = request.form.get('participation_type', 'Attendee').strip()
    certificate_details = request.form.get('certificate_details', '').strip()

    if not student_id or not title or not organizer or not event_date:
        flash('Student, title, organizer, and date are required.', 'error')
        return redirect(url_for('seminars_page'))

    try:
        sem_id = db.execute("""
            INSERT INTO seminars (student_id, title, organizer, event_date, participation_type, certificate_details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (int(student_id), title, organizer, event_date, participation_type, certificate_details))

        google_sheets.queue_outbox_event('Seminars', sem_id, 'UPSERT', {
            'id': sem_id,
            'student_id': int(student_id),
            'title': title,
            'organizer': organizer,
            'event_date': event_date,
            'participation_type': participation_type,
            'certificate_details': certificate_details
        })
        flash(f'Seminar "{title}" recorded successfully.', 'success')
    except Exception as e:
        flash(f'Error recording seminar: {str(e)}', 'error')

    return redirect(url_for('seminars_page'))

# -----------------------------------------------------------------------------
# Activities Portfolio Page
# -----------------------------------------------------------------------------
@app.route('/activities')
def activities_page():
    """Dedicated Extracurricular Activities Portfolio with Category Filters."""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    student_id = request.args.get('student_id', '').strip()

    query = """
        SELECT a.*, s.full_name, s.student_code
        FROM activities a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (a.title LIKE %s OR a.achievement LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])
    if category:
        query += " AND a.category = %s"
        params.append(category)
    if student_id and student_id.isdigit():
        query += " AND a.student_id = %s"
        params.append(int(student_id))

    query += " ORDER BY a.event_date DESC"
    activities = db.query_all(query, tuple(params))

    stats = db.query_one("""
        SELECT 
            COUNT(*) AS total_activities,
            SUM(CASE WHEN category = 'Hackathon' THEN 1 ELSE 0 END) AS hackathons,
            SUM(CASE WHEN achievement IN ('Winner', '1st Runner Up') THEN 1 ELSE 0 END) AS awards,
            SUM(CASE WHEN category = 'Technical' THEN 1 ELSE 0 END) AS technical
        FROM activities
    """) or {'total_activities': 0, 'hackathons': 0, 'awards': 0, 'technical': 0}

    all_students = db.query_all("SELECT id, full_name, student_code FROM students ORDER BY full_name ASC")

    return render_template(
        'activities.html',
        activities=activities,
        stats=stats,
        all_students=all_students,
        search=search,
        current_category=category,
        current_student_id=student_id
    )

@app.route('/activities/create', methods=['POST'])
def activity_create_master():
    """Add activity from master activities directory."""
    student_id = request.form.get('student_id', '').strip()
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Technical').strip()
    description = request.form.get('description', '').strip()
    event_date = request.form.get('event_date', '').strip()
    achievement = request.form.get('achievement', '').strip()
    certificate_details = request.form.get('certificate_details', '').strip()

    if not student_id or not title or not event_date:
        flash('Student, title, and event date are required.', 'error')
        return redirect(url_for('activities_page'))

    try:
        act_id = db.execute("""
            INSERT INTO activities (student_id, title, category, description, event_date, achievement, certificate_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (int(student_id), title, category, description, event_date, achievement, certificate_details))

        google_sheets.queue_outbox_event('Activities', act_id, 'UPSERT', {
            'id': act_id,
            'student_id': int(student_id),
            'title': title,
            'category': category,
            'description': description,
            'event_date': event_date,
            'achievement': achievement,
            'certificate_details': certificate_details
        })
        flash(f'Activity "{title}" added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding activity: {str(e)}', 'error')

    return redirect(url_for('activities_page'))

# Backward compatibility route for portfolio
@app.route('/portfolio')
def portfolio_directory():
    return redirect(url_for('activities_page'))

@app.route('/students/<int:student_id>/seminars/add', methods=['POST'])
def seminar_add(student_id):
    title = request.form.get('title', '').strip()
    organizer = request.form.get('organizer', '').strip()
    event_date = request.form.get('event_date', '').strip()
    participation_type = request.form.get('participation_type', 'Attendee').strip()
    certificate_details = request.form.get('certificate_details', '').strip()

    try:
        sem_id = db.execute("""
            INSERT INTO seminars (student_id, title, organizer, event_date, participation_type, certificate_details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, title, organizer, event_date, participation_type, certificate_details))

        google_sheets.queue_outbox_event('Seminars', sem_id, 'UPSERT', {
            'id': sem_id,
            'student_id': student_id,
            'title': title,
            'organizer': organizer,
            'event_date': event_date,
            'participation_type': participation_type,
            'certificate_details': certificate_details
        })

        flash(f'Seminar "{title}" recorded.', 'success')
    except Exception as e:
        flash(f'Error adding seminar: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/seminars/<int:seminar_id>/delete', methods=['POST'])
def seminar_delete(seminar_id):
    sem = db.query_one("SELECT student_id FROM seminars WHERE id = %s", (seminar_id,))
    if sem:
        db.execute("DELETE FROM seminars WHERE id = %s", (seminar_id,))
        google_sheets.queue_outbox_event('Seminars', seminar_id, 'DELETE', {'id': seminar_id})
        flash('Seminar removed.', 'success')
        return redirect(url_for('student_profile', student_id=sem['student_id']))
    return redirect(url_for('portfolio_directory'))

@app.route('/students/<int:student_id>/activities/add', methods=['POST'])
def activity_add(student_id):
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Technical').strip()
    description = request.form.get('description', '').strip()
    event_date = request.form.get('event_date', '').strip()
    achievement = request.form.get('achievement', '').strip()
    certificate_details = request.form.get('certificate_details', '').strip()

    try:
        act_id = db.execute("""
            INSERT INTO activities (student_id, title, category, description, event_date, achievement, certificate_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (student_id, title, category, description, event_date, achievement, certificate_details))

        google_sheets.queue_outbox_event('Activities', act_id, 'UPSERT', {
            'id': act_id,
            'student_id': student_id,
            'title': title,
            'category': category,
            'description': description,
            'event_date': event_date,
            'achievement': achievement,
            'certificate_details': certificate_details
        })

        flash(f'Activity "{title}" added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding activity: {str(e)}', 'error')

    return redirect(url_for('student_profile', student_id=student_id))

@app.route('/activities/<int:activity_id>/delete', methods=['POST'])
def activity_delete(activity_id):
    act = db.query_one("SELECT student_id FROM activities WHERE id = %s", (activity_id,))
    if act:
        db.execute("DELETE FROM activities WHERE id = %s", (activity_id,))
        google_sheets.queue_outbox_event('Activities', activity_id, 'DELETE', {'id': activity_id})
        flash('Activity record removed.', 'success')
        return redirect(url_for('student_profile', student_id=act['student_id']))
    return redirect(url_for('portfolio_directory'))

# -----------------------------------------------------------------------------
# Google Sheets Integration Page & Actions
# -----------------------------------------------------------------------------
@app.route('/sync')
def sync_page():
    """Live Google Sheets synchronization status dashboard and audit log."""
    status_data = google_sheets.get_sync_status()
    return render_template('sync.html', sync_status=status_data)

@app.route('/sync/trigger-bulk', methods=['POST'])
def sync_trigger_bulk():
    """Manual trigger to process outbox queue and push a complete snapshot of all 7 relational tables to Google Sheets."""
    # First flush pending outbox queue
    outbox_res = google_sheets.process_sync_outbox(limit=50)
    
    # Then execute full snapshot sync
    res = google_sheets.push_bulk_snapshot_to_sheets()
    if res.get('status') == 'SUCCESS':
        details = res.get('details', {})
        counts = details.get('synced_counts', {})
        counts_str = ', '.join([f"{k}: {v}" for k, v in counts.items()])
        flash(f'Google Sheets sync succeeded! Updated 7 worksheets ({counts_str}).', 'success')
    elif res.get('status') == 'SKIPPED':
        flash('Google Sheets Webhook URL is not configured.', 'warning')
    else:
        flash(f"Sync error: {res.get('error')}", 'error')

    return redirect(url_for('sync_page'))

@app.route('/sync/process-outbox', methods=['POST'])
def sync_process_outbox():
    """Process pending outbox queue events."""
    res = google_sheets.process_sync_outbox(limit=25)
    flash(f"Outbox processing completed: {res.get('success', 0)} succeeded, {res.get('failed', 0)} failed.", 'info')
    return redirect(url_for('sync_page'))

# -----------------------------------------------------------------------------
# Excel Export
# -----------------------------------------------------------------------------
@app.route('/export/excel')
def export_excel_file():
    """Exports all 7 relational database tables into a clean multi-tab .xlsx file."""
    try:
        buffer = export_excel.generate_academic_workbook()
        filename = f"Student_Academic_Progression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f"Error generating Excel workbook: {str(e)}", 'error')
        return redirect(url_for('dashboard'))

# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, message="The requested page or record could not be found."), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, message="An internal database or server error occurred. Please try again."), 500

if __name__ == '__main__':
    # Local development server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
