// student_registration.js
// Handles loading classes based on selected school

frappe.ready(function() {
    console.log('Student Registration JS loaded');

    const schoolSelect = document.getElementById('school');
    const classSelect = document.getElementById('student_class');

    // Ensure class select starts disabled
    if (classSelect) {
        classSelect.innerHTML = '<option value="">Select school first</option>';
        classSelect.disabled = true;
    }

    if (schoolSelect) {
        schoolSelect.addEventListener('change', function() {
            const selectedSchool = this.value;
            console.log('School changed to:', selectedSchool);

            if (classSelect) {
                classSelect.innerHTML = '<option value="">Select class</option>';
                classSelect.disabled = true;
                classSelect.value = '';
            }

            if (selectedSchool) {
                loadClassesBySchool(selectedSchool);
            } else {
                if (classSelect) {
                    classSelect.innerHTML = '<option value="">Select school first</option>';
                    classSelect.disabled = true;
                }
            }
        });
    }

    // Clear error state on interaction
    document.querySelectorAll('input, select').forEach(function(field) {
        field.addEventListener('change', function(e) { e.target.classList.remove('error'); });
        field.addEventListener('input',  function(e) { e.target.classList.remove('error'); });
    });
});

// ---------------------------------------------------------------------------
// Class loading
// ---------------------------------------------------------------------------

async function loadClassesBySchool(school) {
    const classSelect = document.getElementById('student_class');

    if (!classSelect || !school) {
        if (classSelect) {
            classSelect.innerHTML = '<option value="">Select school first</option>';
            classSelect.disabled = true;
        }
        return;
    }

    classSelect.innerHTML = '<option value="">Loading classes\u2026</option>';
    classSelect.disabled = true;

    try {
        const csrf = getCsrfToken();
        const resp = await fetch(
            '/api/method/school.www.student_registration.get_classes_by_school',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Frappe-CSRF-Token': csrf
                },
                credentials: 'include',
                body: JSON.stringify({ school: school })
            }
        );

        const r = await resp.json();

        if (r.message && r.message.length > 0) {
            classSelect.innerHTML = '<option value="">Select class</option>';
            r.message.forEach(function(cls) {
                const option = document.createElement('option');
                option.value = cls.name;
                option.textContent = cls.name;
                classSelect.appendChild(option);
            });
            classSelect.disabled = false;
        } else {
            classSelect.innerHTML = '<option value="">No classes available</option>';
            classSelect.disabled = true;
        }
    } catch (e) {
        console.error('Error loading classes:', e);
        classSelect.innerHTML = '<option value="">Error loading classes</option>';
        classSelect.disabled = true;
    }
}

// ---------------------------------------------------------------------------
// CSRF helper
// ---------------------------------------------------------------------------

function getCsrfToken() {
    return (
        document.cookie
            .split(';')
            .map(function(c) { return c.trim(); })
            .find(function(c) { return c.startsWith('csrf_token='); }) || ''
    ).replace('csrf_token=', '');
}

// ---------------------------------------------------------------------------
// Guardian fields toggle
// ---------------------------------------------------------------------------

function toggleGuardianFields() {
    const guardianIs = document.getElementById('if_guardian_is');
    const guardianFields = document.querySelectorAll('.g-other');

    if (guardianIs && guardianIs.value === 'Other') {
        guardianFields.forEach(function(f) { f.style.display = 'block'; });
    } else {
        guardianFields.forEach(function(f) { f.style.display = 'none'; });
    }
}

// ---------------------------------------------------------------------------
// Field helper
// ---------------------------------------------------------------------------

function getFieldValue(fieldId) {
    const field = document.getElementById(fieldId);
    return field ? field.value.trim() : '';
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function validateForm() {
    // Only validate step-1 required fields when step 1 is active
    const step1Active = document.getElementById('step1') &&
                        document.getElementById('step1').classList.contains('active');

    const requiredFields = ['school', 'first_name', 'last_name', 'student_type'];

    // Only require student_class if the select is enabled (classes have loaded)
    const classSelect = document.getElementById('student_class');
    if (classSelect && !classSelect.disabled) {
        requiredFields.push('student_class');
    }

    let isValid = true;

    requiredFields.forEach(function(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            if (!field.value) {
                field.classList.add('error');
                isValid = false;
            } else {
                field.classList.remove('error');
            }
        }
    });

    // Payment fields only required when billing is enabled (step 4)
    const billEnabled = document.body.getAttribute('data-bill-enabled') === 'true';
    if (billEnabled) {
        ['account', 'payment_method'].forEach(function(fieldId) {
            const field = document.getElementById(fieldId);
            if (field) {
                if (!field.value) {
                    field.classList.add('error');
                    isValid = false;
                } else {
                    field.classList.remove('error');
                }
            }
        });
    }

    return isValid;
}

// ---------------------------------------------------------------------------
// Step navigation
// ---------------------------------------------------------------------------

function goToStep(step) {
    const currentStep = document.querySelector('.form-step.active');
    const nextStep    = document.getElementById('step' + step);

    if (!currentStep || !nextStep) return;

    const currentNum = parseInt(currentStep.id.replace('step', ''), 10);

    // Only validate when moving forward from step 1
    if (step > currentNum && currentNum === 1 && !validateForm()) {
        showError('Please fill in all required fields (School, First Name, Last Name, Student Type, and Class).');
        return;
    }

    currentStep.classList.remove('active');
    nextStep.classList.add('active');

    document.querySelectorAll('.step-tab').forEach(function(tab, index) {
        if (index + 1 === step) {
            tab.classList.add('active');
            tab.classList.remove('done');
        } else if (index + 1 < step) {
            tab.classList.add('done');
            tab.classList.remove('active');
        } else {
            tab.classList.remove('active', 'done');
        }
    });

    if (step === 5) buildReview();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---------------------------------------------------------------------------
// Review builder  (fixed — no stray Chinese characters)
// ---------------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function buildReview() {
    const reviewContent = document.getElementById('reviewContent');
    if (!reviewContent) return;

    const fields = {
        'School':        getFieldValue('school'),
        'Student Name':  [getFieldValue('first_name'), getFieldValue('second_name'), getFieldValue('last_name')].filter(Boolean).join(' '),
        'Class':         getFieldValue('student_class'),
        'Student Type':  getFieldValue('student_type'),
        'Gender':        getFieldValue('gender'),
        'Date of Birth': getFieldValue('date_of_birth'),
        'Father Name':   getFieldValue('father_name'),
        'Mother Name':   getFieldValue('mother_name'),
        'Father Phone':  getFieldValue('phone_number'),
        'Mother Phone':  getFieldValue('mother_phone'),
        'Guardian Is':   getFieldValue('if_guardian_is'),
        'Guardian Name': getFieldValue('guardian_name'),
        'Address':       getFieldValue('current_address')
    };

    let html = '<table style="width:100%;border-collapse:collapse">';
    let i = 0;

    for (const [label, value] of Object.entries(fields)) {
        if (!value) continue;
        const bg = i % 2 ? '#fff' : '#fdfbf7';
        html += '<tr style="background:' + bg + '">' +
            '<td style="padding:9px 14px;font-size:11px;font-weight:600;text-transform:uppercase;' +
                'color:#7f8c8d;width:40%;border-bottom:1px solid #f9f5ee">' + escapeHtml(label) + '<\/td>' +
            '<td style="padding:9px 14px;font-size:14px;border-bottom:1px solid #f9f5ee">' + escapeHtml(value) + '<\/td>' +
            '<\/tr>';
        i++;
    }

    html += '<\/table>';
    reviewContent.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Error display
// ---------------------------------------------------------------------------

function showError(message) {
    const errorDiv = document.getElementById('globalError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(function() { errorDiv.classList.remove('show'); }, 5000);
    } else {
        alert(message);
    }
}

// ---------------------------------------------------------------------------
// CSRF helper – fetches a fresh token from Frappe for guest sessions
// ---------------------------------------------------------------------------
async function getFrappeCSRF() {
    // 1. Try the cookie first (works for logged-in users)
    const fromCookie = document.cookie
        .split(';')
        .map(function(c) { return c.trim(); })
        .find(function(c) { return c.startsWith('csrf_token='); });

    if (fromCookie) {
        const token = decodeURIComponent(fromCookie.split('=')[1]);
        // Frappe sets 'Fetch' as the guest placeholder – means we need a real one
        if (token && token !== 'Fetch') return token;
    }

    // 2. For guest sessions, fetch a real token from Frappe
    try {
        const r = await fetch('/api/method/frappe.auth.get_logged_user', {
            method: 'GET',
            credentials: 'same-origin'
        });
        // After this request Frappe sets the csrf_token cookie properly
        const fromCookieAfter = document.cookie
            .split(';')
            .map(function(c) { return c.trim(); })
            .find(function(c) { return c.startsWith('csrf_token='); });
        if (fromCookieAfter) {
            return decodeURIComponent(fromCookieAfter.split('=')[1]);
        }
    } catch (e) {
        console.warn('Could not refresh CSRF token:', e);
    }

    return '';
}

// ---------------------------------------------------------------------------
// Submission
// ---------------------------------------------------------------------------
async function submitRegistration() {
    if (!validateForm()) {
        showError('Please fill in all required fields.');
        return false;
    }

    const declaration = document.getElementById('declaration');
    if (!declaration || !declaration.checked) {
        showError('Please accept the declaration before submitting.');
        return false;
    }

    const submitBtn = document.getElementById('submitBtn');
    const btnText   = document.getElementById('btnText');

    if (submitBtn) {
        submitBtn.disabled = true;
        if (btnText) btnText.innerHTML = '<span class="spinner"></span> Submitting\u2026';
    }

    const formData = {
        school:                          getFieldValue('school'),
        first_name:                      getFieldValue('first_name'),
        second_name:                     getFieldValue('second_name'),
        last_name:                       getFieldValue('last_name'),
        date_of_birth:                   getFieldValue('date_of_birth'),
        gender:                          getFieldValue('gender'),
        student_phone_number:            getFieldValue('student_phone_number'),
        student_class:                   getFieldValue('student_class'),
        student_type:                    getFieldValue('student_type'),
        religion:                        getFieldValue('religion'),
        date_of_admission:               getFieldValue('date_of_admission'),
        national_identification_number:  getFieldValue('national_identification_number'),
        local_identification_number:     getFieldValue('local_identification_number'),
        previous_school_details:         getFieldValue('previous_school_details'),
        medical_history:                 getFieldValue('medical_history'),
        portal_email:                    getFieldValue('portal_email'),
        father_name:                     getFieldValue('father_name'),
        mother_name:                     getFieldValue('mother_name'),
        phone_number:                    getFieldValue('phone_number'),
        mother_phone:                    getFieldValue('mother_phone'),
        father_email:                    getFieldValue('father_email'),
        mother_email:                    getFieldValue('mother_email'),
        father_occupation:               getFieldValue('father_occupation'),
        mother_occupation:               getFieldValue('mother_occupation'),
        if_guardian_is:                  getFieldValue('if_guardian_is'),
        guardian_name:                   getFieldValue('guardian_name'),
        guardian_relation:               getFieldValue('guardian_relation'),
        guardian_phone:                  getFieldValue('guardian_phone'),
        guardian_email:                  getFieldValue('guardian_email'),
        guardian_occupation:             getFieldValue('guardian_occupation'),
        guardian_address:                getFieldValue('guardian_address'),
        current_address:                 getFieldValue('current_address'),
        permanent_address:               getFieldValue('permanent_address'),
        account:                         getFieldValue('account'),
        payment_method:                  getFieldValue('payment_method')
    };

    try {
        // Always get a fresh CSRF token right before submitting
        const csrfToken = await getFrappeCSRF();

        const response = await fetch(
            '/api/method/school.www.student_registration.submit_registration',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Frappe-CSRF-Token': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({ data: JSON.stringify(formData) })
            }
        );

        // Frappe returns 417 when CSRF fails – give a clear message
        if (response.status === 417) {
            throw new Error('CSRF validation failed (417). Please refresh the page and try again.');
        }

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const result = await response.json();

        if (result.message && result.message.success) {
            document.querySelectorAll('.form-step').forEach(function(step) {
                step.style.display = 'none';
            });
            const successScreen = document.getElementById('successScreen');
            if (successScreen) {
                successScreen.classList.add('show');
                document.getElementById('successMsg').textContent = result.message.message;
                document.getElementById('refBadge').textContent   = 'Reference: ' + result.message.name;
            }
        } else {
            const errorMsg = (result.message && result.message.message) || 'Submission failed. Please try again.';
            showError(errorMsg);
            if (submitBtn) {
                submitBtn.disabled = false;
                if (btnText) btnText.textContent = 'Submit Application';
            }
        }

    } catch (error) {
        console.error('Submission error:', error);
        showError(error.message || 'Network error. Please check your connection and try again.');
        if (submitBtn) {
            submitBtn.disabled = false;
            if (btnText) btnText.textContent = 'Submit Application';
        }
    }

    return false;
}
// ---------------------------------------------------------------------------
// Global exports
// ---------------------------------------------------------------------------

window.loadClassesBySchool    = loadClassesBySchool;
window.toggleGuardianFields   = toggleGuardianFields;
window.submitRegistration     = submitRegistration;
window.goToStep               = goToStep;
window.buildReview            = buildReview;
window.validateForm           = validateForm;
