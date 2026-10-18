-- ==============================================================================
-- DATABASE SCHEMA: Student Academic Progression & Portfolio Management System
-- Demonstrating 3NF Relational Design, Constraints, Keys, and Indexes
-- ==============================================================================

-- 1. Students Table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    admission_year INTEGER NOT NULL,
    current_status VARCHAR(20) NOT NULL DEFAULT 'Active', -- 'Active', 'On Leave', 'Graduated', 'Suspended'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_students_code ON students(student_code);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(current_status);
CREATE INDEX IF NOT EXISTS idx_students_admission ON students(admission_year);

-- 2. School Records Table (10th, 12th / Diploma)
CREATE TABLE IF NOT EXISTS school_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    education_level VARCHAR(30) NOT NULL, -- '10th Secondary', '12th Higher Secondary', 'Diploma'
    institution VARCHAR(150) NOT NULL,
    board VARCHAR(100) NOT NULL,          -- 'CBSE', 'ICSE', 'State Board'
    passing_year INTEGER NOT NULL,
    max_marks DECIMAL(6, 2) NOT NULL,
    obtained_marks DECIMAL(6, 2) NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_school_student ON school_records(student_id);

-- 3. Semesters Table
CREATE TABLE IF NOT EXISTS semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    semester_number INTEGER NOT NULL,     -- 1 to 8
    academic_year VARCHAR(15) NOT NULL,   -- e.g. '2023-2024'
    credits DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    sgpa DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    cgpa DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, semester_number),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_semesters_student ON semesters(student_id);
CREATE INDEX IF NOT EXISTS idx_semesters_num ON semesters(semester_number);

-- 4. Student Marks Table
CREATE TABLE IF NOT EXISTS student_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_id INTEGER NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    subject_name VARCHAR(120) NOT NULL,
    credits DECIMAL(3, 1) NOT NULL,
    max_marks DECIMAL(5, 2) NOT NULL DEFAULT 100.0,
    obtained_marks DECIMAL(5, 2) NOT NULL,
    grade VARCHAR(5) NOT NULL,             -- 'O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(semester_id, subject_code),
    FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_marks_semester ON student_marks(semester_id);
CREATE INDEX IF NOT EXISTS idx_marks_subject ON student_marks(subject_code);

-- 5. Gap Years Table
CREATE TABLE IF NOT EXISTS gap_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    reason VARCHAR(150) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gap_student ON gap_years(student_id);

-- 6. Seminars Table
CREATE TABLE IF NOT EXISTS seminars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    organizer VARCHAR(150) NOT NULL,
    event_date DATE NOT NULL,
    participation_type VARCHAR(50) NOT NULL, -- 'Attendee', 'Presenter', 'Organizer', 'Keynote'
    certificate_details VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_seminars_student ON seminars(student_id);
CREATE INDEX IF NOT EXISTS idx_seminars_date ON seminars(event_date);

-- 7. Activities Table (Co-curricular & Extracurricular)
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,          -- 'Technical', 'Sports', 'Cultural', 'Social/NSS', 'Hackathon'
    description TEXT,
    event_date DATE NOT NULL,
    achievement VARCHAR(100),              -- 'Winner', '1st Runner Up', 'Finalist', 'Participant'
    certificate_details VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activities_student ON activities(student_id);
CREATE INDEX IF NOT EXISTS idx_activities_cat ON activities(category);

-- 8. Sync Log Table (Audit trail of external spreadsheet synchronization)
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name VARCHAR(50) NOT NULL,      -- 'Students', 'SchoolRecords', etc.
    record_id INTEGER,
    operation VARCHAR(20) NOT NULL,        -- 'INSERT', 'UPDATE', 'DELETE', 'BULK_SYNC'
    status VARCHAR(20) NOT NULL,           -- 'SUCCESS', 'FAILED', 'PENDING'
    payload TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_log(entity_name);

-- 9. Sync Outbox Table (Durable Queue for Reliable Background Synchronization)
CREATE TABLE IF NOT EXISTS sync_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    operation VARCHAR(20) NOT NULL,        -- 'UPSERT', 'DELETE'
    payload TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'SYNCED', 'FAILED'
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outbox_status ON sync_outbox(status);
