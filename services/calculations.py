from config import Config

def get_grade_and_point(obtained_marks: float, max_marks: float = 100.0) -> tuple:
    """
    Computes letter grade and grade point (10-point scale) based on percentage.
    Grading standard:
      90-100% -> 'O'  (10.0 GP) - Outstanding
      80-89%  -> 'A+' (9.0 GP)  - Excellent
      70-79%  -> 'A'  (8.0 GP)  - Very Good
      60-69%  -> 'B+' (7.0 GP)  - Good
      55-59%  -> 'B'  (6.0 GP)  - Above Average
      50-54%  -> 'C'  (5.0 GP)  - Average
      40-49%  -> 'P'  (4.0 GP)  - Pass
      < 40%   -> 'F'  (0.0 GP)  - Fail
    """
    if max_marks <= 0:
        return 'F', 0.0
    pct = (obtained_marks / max_marks) * 100.0
    
    if pct >= 90.0:
        return 'O', 10.0
    elif pct >= 80.0:
        return 'A+', 9.0
    elif pct >= 70.0:
        return 'A', 8.0
    elif pct >= 60.0:
        return 'B+', 7.0
    elif pct >= 55.0:
        return 'B', 6.0
    elif pct >= 50.0:
        return 'C', 5.0
    elif pct >= 40.0:
        return 'P', 4.0
    else:
        return 'F', 0.0

def calculate_percentage(obtained_marks: float, max_marks: float) -> float:
    """
    Calculates percentage rounded to 2 decimal places.
    """
    if max_marks <= 0:
        return 0.0
    return round((obtained_marks / max_marks) * 100.0, 2)

def calculate_sgpa(subject_marks: list) -> tuple:
    """
    Calculates total credits and SGPA from a list of subject marks dicts.
    Each dict should have: credits, obtained_marks, max_marks (or grade).
    Formula: SGPA = Sum(Credits * GradePoint) / Sum(Credits)
    Returns: (total_credits, sgpa)
    """
    if not subject_marks:
        return 0.0, 0.00
    
    total_credits = 0.0
    total_credit_points = 0.0

    for m in subject_marks:
        credits = float(m.get('credits', 0.0))
        grade = m.get('grade')
        if not grade:
            obtained = float(m.get('obtained_marks', 0.0))
            max_m = float(m.get('max_marks', 100.0))
            grade, gp = get_grade_and_point(obtained, max_m)
        else:
            gp = Config.GRADING_SYSTEM.get(grade, {}).get('gp', 0.0)
            
        total_credits += credits
        total_credit_points += (credits * gp)
        
    if total_credits <= 0:
        return 0.0, 0.00
    
    sgpa = round(total_credit_points / total_credits, 2)
    return round(total_credits, 1), sgpa

def recalculate_student_cgpa(semesters: list) -> list:
    """
    Recalculates progressive CGPA for a student's ordered semesters list.
    Formula: Cumulative CGPA at Semester n = 
             Sum(Semester Credits * SGPA for 1..n) / Sum(Semester Credits for 1..n)
    Returns the list with updated 'cgpa' fields.
    """
    sorted_sems = sorted(semesters, key=lambda s: int(s.get('semester_number', 0)))
    running_weighted_points = 0.0
    running_credits = 0.0
    
    for s in sorted_sems:
        credits = float(s.get('credits', 0.0))
        sgpa = float(s.get('sgpa', 0.0))
        running_credits += credits
        running_weighted_points += (credits * sgpa)
        if running_credits > 0:
            s['cgpa'] = round(running_weighted_points / running_credits, 2)
        else:
            s['cgpa'] = 0.00
            
    return sorted_sems
