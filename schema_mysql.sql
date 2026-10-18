-- ==============================================================================
-- MYSQL / TIDB CLOUD NATIVE SCHEMA
-- ==============================================================================

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_code VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    admission_year INT NOT NULL,
    current_status VARCHAR(20) NOT NULL DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_students_code (student_code),
    INDEX idx_students_status (current_status),
    INDEX idx_students_admission (admission_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS school_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    education_level VARCHAR(30) NOT NULL,
    institution VARCHAR(150) NOT NULL,
    board VARCHAR(100) NOT NULL,
    passing_year INT NOT NULL,
    max_marks DECIMAL(6, 2) NOT NULL,
    obtained_marks DECIMAL(6, 2) NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_school_student (student_id),
    CONSTRAINT fk_school_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS semesters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    semester_number INT NOT NULL,
    academic_year VARCHAR(15) NOT NULL,
    credits DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    sgpa DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    cgpa DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_sem (student_id, semester_number),
    INDEX idx_semesters_student (student_id),
    INDEX idx_semesters_num (semester_number),
    CONSTRAINT fk_sem_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS student_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    semester_id INT NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    subject_name VARCHAR(120) NOT NULL,
    credits DECIMAL(3, 1) NOT NULL,
    max_marks DECIMAL(5, 2) NOT NULL DEFAULT 100.00,
    obtained_marks DECIMAL(5, 2) NOT NULL,
    grade VARCHAR(5) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sem_sub (semester_id, subject_code),
    INDEX idx_marks_semester (semester_id),
    INDEX idx_marks_subject (subject_code),
    CONSTRAINT fk_marks_sem FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gap_years (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    start_year INT NOT NULL,
    end_year INT NOT NULL,
    reason VARCHAR(150) NOT NULL,
    remarks TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_gap_student (student_id),
    CONSTRAINT fk_gap_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS seminars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    organizer VARCHAR(150) NOT NULL,
    event_date DATE NOT NULL,
    participation_type VARCHAR(50) NOT NULL,
    certificate_details VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_seminars_student (student_id),
    INDEX idx_seminars_date (event_date),
    CONSTRAINT fk_seminars_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    achievement VARCHAR(100),
    certificate_details VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_activities_student (student_id),
    INDEX idx_activities_cat (category),
    CONSTRAINT fk_activities_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_name VARCHAR(50) NOT NULL,
    record_id INT,
    operation VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    payload LONGTEXT,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME,
    INDEX idx_sync_status (status),
    INDEX idx_sync_entity (entity_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_outbox (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    operation VARCHAR(20) NOT NULL,
    payload LONGTEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INT DEFAULT 0,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_outbox_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
