-- ==============================================================================
-- DEMO SEED DATA: Realistic Fictional Student Academic Records
-- ==============================================================================

-- 1. Students
INSERT INTO students (id, student_code, full_name, email, admission_year, current_status) VALUES
(1, 'CS2022001', 'Aarav Sharma', 'aarav.sharma@demo.edu', 2022, 'Active'),
(2, 'CS2022014', 'Diya Patel', 'diya.patel@demo.edu', 2022, 'Active'),
(3, 'CS2021045', 'Rohan Verma', 'rohan.verma@demo.edu', 2021, 'Active'),
(4, 'CS2020088', 'Ananya Iyer', 'ananya.iyer@demo.edu', 2020, 'Graduated'),
(5, 'CS2023019', 'Kabir Sen', 'kabir.sen@demo.edu', 2023, 'On Leave');

-- 2. School Records (10th & 12th)
INSERT INTO school_records (id, student_id, education_level, institution, board, passing_year, max_marks, obtained_marks, percentage) VALUES
(1, 1, '10th Secondary', 'St. Xavier High School', 'CBSE', 2020, 500.0, 465.0, 93.00),
(2, 1, '12th Higher Secondary', 'DPS Public School', 'CBSE', 2022, 500.0, 452.0, 90.40),
(3, 2, '10th Secondary', 'Modern English Academy', 'ICSE', 2020, 600.0, 558.0, 93.00),
(4, 2, '12th Higher Secondary', 'National Junior College', 'State Board', 2022, 600.0, 528.0, 88.00),
(5, 3, '10th Secondary', 'DAV Public School', 'CBSE', 2018, 500.0, 410.0, 82.00),
(6, 3, '12th Higher Secondary', 'Kendriya Vidyalaya', 'CBSE', 2020, 500.0, 395.0, 79.00),
(7, 4, '10th Secondary', 'St. Thomas High School', 'ICSE', 2018, 600.0, 570.0, 95.00),
(8, 4, '12th Higher Secondary', 'Loyola Junior College', 'State Board', 2020, 600.0, 564.0, 94.00),
(9, 5, '10th Secondary', 'Don Bosco School', 'CBSE', 2021, 500.0, 430.0, 86.00),
(10, 5, '12th Higher Secondary', 'Army Public School', 'CBSE', 2023, 500.0, 420.0, 84.00);

-- 3. Semesters
-- Student 1 (Aarav Sharma - 2022 batch, 4 completed semesters)
INSERT INTO semesters (id, student_id, semester_number, academic_year, credits, sgpa, cgpa) VALUES
(1, 1, 1, '2022-2023', 20.0, 8.85, 8.85),
(2, 1, 2, '2022-2023', 21.0, 9.10, 8.98),
(3, 1, 3, '2023-2024', 22.0, 8.70, 8.88),
(4, 1, 4, '2023-2024', 21.0, 9.25, 8.97);

-- Student 2 (Diya Patel - 2022 batch, 3 completed semesters)
INSERT INTO semesters (id, student_id, semester_number, academic_year, credits, sgpa, cgpa) VALUES
(5, 2, 1, '2022-2023', 20.0, 9.30, 9.30),
(6, 2, 2, '2022-2023', 21.0, 9.45, 9.38),
(7, 2, 3, '2023-2024', 22.0, 9.20, 9.31);

-- Student 3 (Rohan Verma - 2021 batch, 4 semesters, had gap year)
INSERT INTO semesters (id, student_id, semester_number, academic_year, credits, sgpa, cgpa) VALUES
(8, 3, 1, '2021-2022', 20.0, 7.40, 7.40),
(9, 3, 2, '2021-2022', 21.0, 7.80, 7.60),
(10, 3, 3, '2022-2023', 22.0, 8.10, 7.78),
(11, 3, 4, '2022-2023', 21.0, 8.35, 7.92);

-- Student 4 (Ananya Iyer - Graduated, 8 semesters demo subset)
INSERT INTO semesters (id, student_id, semester_number, academic_year, credits, sgpa, cgpa) VALUES
(12, 4, 1, '2020-2021', 20.0, 9.50, 9.50),
(13, 4, 2, '2020-2021', 21.0, 9.60, 9.55),
(14, 4, 3, '2021-2022', 22.0, 9.75, 9.62),
(15, 4, 4, '2021-2022', 21.0, 9.80, 9.67);

-- Student 5 (Kabir Sen - 1 semester completed)
INSERT INTO semesters (id, student_id, semester_number, academic_year, credits, sgpa, cgpa) VALUES
(16, 5, 1, '2023-2024', 20.0, 8.20, 8.20);

-- 4. Student Marks (Representative detailed subject marks)
INSERT INTO student_marks (id, semester_id, subject_code, subject_name, credits, max_marks, obtained_marks, grade) VALUES
-- Semester 1 for Aarav Sharma
(1, 1, 'CS101', 'Programming in C', 4.0, 100.0, 88.0, 'A+'),
(2, 1, 'MA101', 'Engineering Mathematics I', 4.0, 100.0, 92.0, 'O'),
(3, 1, 'PH101', 'Applied Physics', 4.0, 100.0, 84.0, 'A+'),
(4, 1, 'EE101', 'Basic Electrical Engineering', 4.0, 100.0, 78.0, 'A'),
(5, 1, 'HS101', 'Professional Communication', 4.0, 100.0, 85.0, 'A+'),

-- Semester 2 for Aarav Sharma
(6, 2, 'CS201', 'Data Structures & Algorithms', 4.0, 100.0, 94.0, 'O'),
(7, 2, 'CS202', 'Object Oriented Programming', 4.0, 100.0, 91.0, 'O'),
(8, 2, 'MA201', 'Discrete Mathematics', 4.0, 100.0, 86.0, 'A+'),
(9, 2, 'EC201', 'Digital Logic Design', 4.0, 100.0, 82.0, 'A+'),
(10, 2, 'CS203', 'DSA Laboratory', 5.0, 100.0, 95.0, 'O'),

-- Semester 3 for Aarav Sharma
(11, 3, 'CS301', 'Database Management Systems', 4.0, 100.0, 90.0, 'O'),
(12, 3, 'CS302', 'Computer Organization & Architecture', 4.0, 100.0, 79.0, 'A'),
(13, 3, 'CS303', 'Design & Analysis of Algorithms', 4.0, 100.0, 87.0, 'A+'),
(14, 3, 'CS304', 'Operating Systems', 4.0, 100.0, 83.0, 'A+'),
(15, 3, 'CS305', 'DBMS Laboratory', 6.0, 100.0, 93.0, 'O'),

-- Semester 1 for Diya Patel
(16, 5, 'CS101', 'Programming in C', 4.0, 100.0, 95.0, 'O'),
(17, 5, 'MA101', 'Engineering Mathematics I', 4.0, 100.0, 96.0, 'O'),
(18, 5, 'PH101', 'Applied Physics', 4.0, 100.0, 89.0, 'A+'),
(19, 5, 'EE101', 'Basic Electrical Engineering', 4.0, 100.0, 88.0, 'A+'),
(20, 5, 'HS101', 'Professional Communication', 4.0, 100.0, 92.0, 'O');

-- 5. Gap Years
INSERT INTO gap_years (id, student_id, start_year, end_year, reason, remarks) VALUES
(1, 3, 2020, 2021, 'Preparation for Engineering Entrance & Medical Recuperation', 'Completed academic prep; medical clearance provided'),
(2, 5, 2024, 2025, 'Family relocation and financial restructuring', 'Granted 1-year authorized study pause by Dean');

-- 6. Seminars
INSERT INTO seminars (id, student_id, title, organizer, event_date, participation_type, certificate_details) VALUES
(1, 1, 'International Conference on Distributed Database Systems', 'IEEE Computer Society', '2023-11-15', 'Presenter', 'CERT-IEEE-DDS-2023-088'),
(2, 1, 'National Workshop on Cloud Native Relational Databases', 'ACM Student Chapter', '2024-02-10', 'Attendee', 'ACM-WS-CNRD-2024-412'),
(3, 2, 'Symposium on Artificial Intelligence and Large Language Models', 'IIT Delhi', '2023-10-22', 'Attendee', 'IITD-AI-SYM-9921'),
(4, 2, 'National Seminar on High Performance Query Processing', 'CSI India', '2024-01-18', 'Presenter', 'CSI-HPQP-2024-102'),
(5, 4, 'Global Summit on Data Engineering & Scalability', 'Data Engineering Forum', '2022-09-05', 'Keynote', 'DEF-SUMMIT-KEY-001');

-- 7. Activities
INSERT INTO activities (id, student_id, title, category, description, event_date, achievement, certificate_details) VALUES
(1, 1, 'Smart India Hackathon 2023', 'Hackathon', 'Developed automated database synchronizer and verification engine', '2023-12-20', 'Winner', 'SIH2023-TEAM-GOLD-09'),
(2, 1, 'University CodeSprint Challenge', 'Technical', 'Competitive programming contest across 40 colleges', '2024-03-05', '1st Runner Up', 'UCS-2024-RANK2'),
(3, 2, 'National Open Source Contribution Sprint', 'Technical', 'Contributed 12 PRs to popular SQL formatting and linting tools', '2023-08-14', 'Winner', 'NOSCS-2023-TOPCONTR'),
(4, 2, 'Annual Inter-College Badminton Championship', 'Sports', 'Represented college in singles and mixed doubles', '2024-02-28', 'Winner', 'SPORTS-BADM-2024-CHAMP'),
(5, 3, 'NSS Blood Donation & Community Health Camp', 'Social/NSS', 'Volunteered for 48 hours managing donor database records', '2023-04-12', 'Participant', 'NSS-CAMP-CERT-2023-88');

-- 8. Sync Log Sample (Initial state)
INSERT INTO sync_log (id, entity_name, record_id, operation, status, payload, error_message, created_at, synced_at, retry_count) VALUES
(1, 'Students', 1, 'BULK_SYNC', 'SUCCESS', '{"records_count": 5}', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0);
