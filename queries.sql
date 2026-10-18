-- ==============================================================================
-- RELATIONAL DBMS QUERIES DEMONSTRATION
-- Project: Student Academic Progression & Portfolio Management System
-- Demonstrating Joins, Aggregate Functions, Subqueries, Group By, Filtering
-- ==============================================================================

-- 1. INNER JOIN: Student Profile with their Latest Academic Semester and CGPA
SELECT 
    s.id AS student_id,
    s.student_code,
    s.full_name,
    s.email,
    s.admission_year,
    s.current_status,
    sem.semester_number,
    sem.academic_year,
    sem.sgpa,
    sem.cgpa
FROM students s
INNER JOIN semesters sem ON s.id = sem.student_id
WHERE sem.semester_number = (
    SELECT MAX(s2.semester_number)
    FROM semesters s2
    WHERE s2.student_id = s.id
)
ORDER BY sem.cgpa DESC;

-- 2. AGGREGATE QUERY: Overall Department Statistics (Average CGPA, Total Students, Max CGPA)
SELECT 
    COUNT(DISTINCT s.id) AS total_students,
    SUM(CASE WHEN s.current_status = 'Active' THEN 1 ELSE 0 END) AS active_students,
    SUM(CASE WHEN s.current_status = 'On Leave' THEN 1 ELSE 0 END) AS on_leave_students,
    SUM(CASE WHEN s.current_status = 'Graduated' THEN 1 ELSE 0 END) AS graduated_students,
    ROUND(AVG(latest_sem.cgpa), 2) AS dept_average_cgpa,
    MAX(latest_sem.cgpa) AS highest_cgpa,
    MIN(latest_sem.cgpa) AS lowest_cgpa
FROM students s
LEFT JOIN (
    SELECT student_id, cgpa
    FROM semesters s1
    WHERE semester_number = (
        SELECT MAX(s2.semester_number) FROM semesters s2 WHERE s2.student_id = s1.student_id
    )
) latest_sem ON s.id = latest_sem.student_id;

-- 3. MULTI-TABLE JOIN: Comprehensive Student Portfolio (Seminars + Activities count)
SELECT 
    s.id,
    s.student_code,
    s.full_name,
    COUNT(DISTINCT sem.id) AS total_semesters_completed,
    COUNT(DISTINCT sem_in.id) AS total_seminars_attended,
    COUNT(DISTINCT act.id) AS total_activities_participated,
    COUNT(DISTINCT CASE WHEN act.achievement IN ('Winner', '1st Runner Up') THEN act.id END) AS awards_won
FROM students s
LEFT JOIN semesters sem ON s.id = sem.student_id
LEFT JOIN seminars sem_in ON s.id = sem_in.student_id
LEFT JOIN activities act ON s.id = act.student_id
GROUP BY s.id, s.student_code, s.full_name
ORDER BY awards_won DESC, total_activities_participated DESC;

-- 4. COMPLEX JOIN & CALCULATION: Recalculate SGPA for each Semester from Subject Marks
SELECT 
    sem.id AS semester_id,
    sem.student_id,
    s.full_name,
    sem.semester_number,
    ROUND(SUM(m.credits), 1) AS total_credits,
    ROUND(SUM(
        m.credits * (
            CASE m.grade
                WHEN 'O'  THEN 10.0
                WHEN 'A+' THEN 9.0
                WHEN 'A'  THEN 8.0
                WHEN 'B+' THEN 7.0
                WHEN 'B'  THEN 6.0
                WHEN 'C'  THEN 5.0
                WHEN 'P'  THEN 4.0
                ELSE 0.0
            END
        )
    ) / SUM(m.credits), 2) AS calculated_sgpa,
    sem.sgpa AS recorded_sgpa
FROM semesters sem
JOIN students s ON sem.student_id = s.id
JOIN student_marks m ON sem.id = m.semester_id
GROUP BY sem.id, sem.student_id, s.full_name, sem.semester_number, sem.sgpa;

-- 5. LEFT JOIN WITH COALESCE: Gap Year Verification
SELECT 
    s.student_code,
    s.full_name,
    s.admission_year,
    COALESCE(gy.start_year || ' - ' || gy.end_year, 'None') AS gap_period,
    COALESCE(gy.reason, 'No gap recorded') AS gap_reason
FROM students s
LEFT JOIN gap_years gy ON s.id = gy.student_id;
