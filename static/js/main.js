// ==============================================================================
// JavaScript Controller: Student Academic Progression Management System
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Mobile Sidebar toggle
    const mobileBtn = document.querySelector('.mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    if (mobileBtn && sidebar) {
        mobileBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });
    }

    // Modal Open/Close triggers
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const modalCloses = document.querySelectorAll('[data-modal-close]');

    modalTriggers.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-modal-target');
            const targetModal = document.getElementById(targetId);
            if (targetModal) {
                targetModal.classList.add('active');
            }
        });
    });

    modalCloses.forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal-overlay');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Close modal on click outside
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
        }
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // Mark Grade Predictor on Input
    const marksInput = document.getElementById('obtained_marks');
    const maxMarksInput = document.getElementById('max_marks');
    const gradeBadge = document.getElementById('calculated_grade_badge');

    function updateGradePrediction() {
        if (!marksInput || !maxMarksInput || !gradeBadge) return;
        const obtained = parseFloat(marksInput.value) || 0;
        const max = parseFloat(maxMarksInput.value) || 100;
        if (max <= 0) return;

        const pct = (obtained / max) * 100;
        let grade = 'F';
        let desc = 'Fail';

        if (pct >= 90) { grade = 'O'; desc = 'Outstanding (10 GP)'; }
        else if (pct >= 80) { grade = 'A+'; desc = 'Excellent (9 GP)'; }
        else if (pct >= 70) { grade = 'A'; desc = 'Very Good (8 GP)'; }
        else if (pct >= 60) { grade = 'B+'; desc = 'Good (7 GP)'; }
        else if (pct >= 55) { grade = 'B'; desc = 'Above Avg (6 GP)'; }
        else if (pct >= 50) { grade = 'C'; desc = 'Average (5 GP)'; }
        else if (pct >= 40) { grade = 'P'; desc = 'Pass (4 GP)'; }

        gradeBadge.textContent = `Grade: ${grade} (${desc})`;
    }

    if (marksInput && maxMarksInput) {
        marksInput.addEventListener('input', updateGradePrediction);
        maxMarksInput.addEventListener('input', updateGradePrediction);
    }

    // Prevent duplicate form submissions and add loading state
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Allow normal submission, but disable button to avoid double-clicks
                setTimeout(() => {
                    submitBtn.disabled = true;
                    submitBtn.style.opacity = '0.7';
                    submitBtn.innerHTML = 'Saving...';
                }, 50);
            }
        });
    });
});
