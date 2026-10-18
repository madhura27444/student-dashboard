# Student Academic Progression & Portfolio Management System

A college-ready, production-grade Relational Database Management System (DBMS) web application built with **Python Flask**, **MySQL / SQLite**, **Chart.js**, **openpyxl**, and **Google Sheets Apps Script Integration**.

---

## 📌 Project Overview

This system manages student academic profiles, educational history (10th/12th), semester-wise marks, SGPA/CGPA calculations, gap years, seminars, and extracurricular portfolios.

### Key DBMS Concepts Implemented
- **Relational Schema (3NF)**: Structured tables with primary keys, foreign keys (`ON DELETE CASCADE`), unique constraints, and indexes.
- **SGPA & CGPA Calculation Engine**: Automatic 10-point scale grade mapping and dynamic cumulative weighted calculation upon any subject marks update.
- **Durable Outbox Queue Pattern**: Database commits complete immediately and queue synchronization events; external Google Sheets updates run asynchronously without blocking the UI.
- **Google Sheets Integration**: Full synchronization across 7 relational worksheets using a custom Google Apps Script Web App.
- **Excel Multi-Tab Export**: Generates `.xlsx` workbooks preserving table structures and relationships.

---

## 🗄️ Relational Database Schema

| Table | Purpose | Key Constraints |
| :--- | :--- | :--- |
| **`students`** | Primary student profile | `id` (PK), `student_code` (UNIQUE), `email` (UNIQUE) |
| **`school_records`** | 10th & 12th education records | `student_id` (FK &rarr; `students.id` CASCADE) |
| **`semesters`** | Semester milestones & progressive CGPA | `(student_id, semester_number)` UNIQUE, `student_id` (FK CASCADE) |
| **`student_marks`** | Subject marks, credits, and letter grades | `(semester_id, subject_code)` UNIQUE, `semester_id` (FK CASCADE) |
| **`gap_years`** | Academic pause & justification history | `student_id` (FK &rarr; `students.id` CASCADE) |
| **`seminars`** | Conferences, workshops, paper presentations | `student_id` (FK &rarr; `students.id` CASCADE) |
| **`activities`** | Co-curricular, sports, hackathons, awards | `student_id` (FK &rarr; `students.id` CASCADE) |
| **`sync_outbox`** | Durable queue for non-blocking Sheets sync | `status` (PENDING, SYNCED, FAILED), `retry_count` |
| **`sync_log`** | Immutable audit trail of external sync events | `status`, `timestamp`, `error_message` |

---

## 📐 Academic Calculation Rules

- **Grade Points (10-Point Scale)**:
  - $\ge 90\% \rightarrow \textbf{O}$ (10.0 GP) &mdash; Outstanding
  - $80 - 89\% \rightarrow \textbf{A+}$ (9.0 GP) &mdash; Excellent
  - $70 - 79\% \rightarrow \textbf{A}$ (8.0 GP) &mdash; Very Good
  - $60 - 69\% \rightarrow \textbf{B+}$ (7.0 GP) &mdash; Good
  - $55 - 59\% \rightarrow \textbf{B}$ (6.0 GP) &mdash; Above Average
  - $50 - 54\% \rightarrow \textbf{C}$ (5.0 GP) &mdash; Average
  - $40 - 49\% \rightarrow \textbf{P}$ (4.0 GP) &mdash; Pass
  - $< 40\% \rightarrow \textbf{F}$ (0.0 GP) &mdash; Fail

- **Semester SGPA**:
  $$\text{SGPA} = \frac{\sum (\text{Subject Credits} \times \text{Grade Point})}{\sum \text{Subject Credits}}$$

- **Cumulative CGPA**:
  $$\text{CGPA}_k = \frac{\sum_{i=1}^k (\text{Semester Credits}_i \times \text{SGPA}_i)}{\sum_{i=1}^k \text{Semester Credits}_i}$$

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/student-academic-progression-system.git
cd student-academic-progression-system
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default mode uses local SQLite (`DB_TYPE=sqlite`), which initializes and seeds demo data automatically on first launch.

### 3. Run the Development Server
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

### 4. Run Automated Tests
```bash
python -m pytest -v
```

---

## 📊 Google Sheets Sync Setup

1. Open your target Google Spreadsheet.
2. Navigate to **Extensions &rarr; Apps Script**.
3. Copy and paste the entire content of [`google_apps_script.js`](google_apps_script.js).
4. Click **Deploy &rarr; New deployment**:
   - Type: **Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Copy the generated Web App URL and set it in your `.env` or cloud hosting environment:
   ```env
   GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/AKfycb.../exec
   ```
6. Click **"Bulk Sync All 7 Tables Now"** on the `/sync` page to populate all 7 sheets instantly.

---

## ☁️ Cloud Deployment (Render + TiDB Cloud)

1. **Database (TiDB Cloud / MySQL)**:
   - Create a free cluster on [TiDB Cloud](https://tidbcloud.com/).
   - Execute [`schema_mysql.sql`](schema_mysql.sql) and [`seed.sql`](seed.sql).
   - Set `DB_TYPE=mysql`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DB_SSL_CA=system`.

2. **Web Service (Render)**:
   - Connect your GitHub repository to Render.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
   - Health Check Path: `/health`
   - Add environment variables (`SECRET_KEY`, `DB_TYPE`, etc.).
