// student_registration.js
// Handles loading classes and sections independently

frappe.ready(function() {
    console.log('Student Registration JS loaded');
    loadAllClasses();
    loadAllSections();
    
    // Add cascade for class -> section
    const classSelect = document.getElementById('student_class');
    if (classSelect) {
        classSelect.addEventListener('change', function() {
            const selectedClass = this.value;
            console.log('Class changed to:', selectedClass);
            loadSectionsByClass(selectedClass);
        });
    }
});

function loadAllClasses() {
    const classSelect = document.getElementById('student_class');
    
    if (!classSelect) {
        console.error('Class select element not found');
        return;
    }
    
    // Use server context first
    try {
        const classesJson = window.all_classes_json || JSON.parse(document.querySelector('script[data-classes]').textContent || '[]');
        console.log('Classes from context:', classesJson);
        if (classesJson && classesJson.length > 0) {
            classSelect.innerHTML = '<option value="">Select class</option>';
            classesJson.forEach(function(cls) {
                const option = document.createElement('option');
                option.value = cls.name;
                option.textContent = cls.name;
                classSelect.appendChild(option);
            });
            return;
        }
    } catch (e) {
        console.log('No context classes, falling back to API');
    }
    
    // Fallback API call
    classSelect.innerHTML = '<option value="">Loading classes...</option>';
    frappe.call({
        method: 'school.www.student_registration.get_all_classes',
        callback: function(r) {
            console.log('Classes loaded:', r.message);
            if (r.message && r.message.length > 0) {
                classSelect.innerHTML = '<option value="">Select class</option>';
                r.message.forEach(function(cls) {
                    const option = document.createElement('option');
                    option.value = cls.name;
                    option.textContent = cls.name;
                    classSelect.appendChild(option);
                });
            } else {
                classSelect.innerHTML = '<option value="">No classes available</option>';
            }
        },
        error: function(e) {
            console.error('Error loading classes:', e);
            classSelect.innerHTML = '<option value="">Error loading classes</option>';
        }
    });
}

function loadAllSections() {
    const sectionSelect = document.getElementById('section');
    
    if (!sectionSelect) {
        console.error('Section select element not found');
        return;
    }
    
    sectionSelect.innerHTML = '<option value="">Loading sections...</option>';
    
    frappe.call({
        method: 'school.www.student_registration.get_all_sections',
        callback: function(r) {
            console.log('Sections loaded:', r.message);
            if (r.message && r.message.length > 0) {
                sectionSelect.innerHTML = '<option value="">Select section</option>';
                r.message.forEach(function(section) {
                    const option = document.createElement('option');
                    option.value = section.name;
                    option.textContent = section.name;
                    sectionSelect.appendChild(option);
                });
            } else {
                sectionSelect.innerHTML = '<option value="">No sections available</option>';
            }
        },
        error: function(e) {
            console.error('Error loading sections:', e);
            sectionSelect.innerHTML = '<option value="">Error loading sections</option>';
        }
    });
}

function loadSectionsByClass(student_class) {
    const sectionSelect = document.getElementById('section');
    
    if (!sectionSelect) return;
    
    if (!student_class) {
        loadAllSections();
        return;
    }
    
    sectionSelect.innerHTML = '<option value="">Loading sections for ' + student_class + '...</option>';
    
    frappe.call({
        method: 'school.www.student_registration.get_sections_by_class',
        args: {
            student_class: student_class
        },
        callback: function(r) {
            console.log('Filtered sections loaded:', r.message);
            if (r.message && r.message.length > 0) {
                sectionSelect.innerHTML = '<option value="">Select section</option>';
                r.message.forEach(function(section) {
                    const option = document.createElement('option');
                    option.value = section.name;
                    option.textContent = section.name;
                    sectionSelect.appendChild(option);
                });
            } else {
                sectionSelect.innerHTML = '<option value="">No sections for this class</option>';
            }
        },
        error: function(e) {
            console.error('Error loading filtered sections:', e);
            sectionSelect.innerHTML = '<option value="">Error loading sections</option>';
        }
    });
}

function toggleGuardianFields() {
    const guardianIs = document.getElementById('if_guardian_is');
    const guardianFields = document.querySelectorAll('.g-other');
    
    if (guardianIs && guardianIs.value === 'Other') {
        guardianFields.forEach(function(field) {
            field.style.display = 'block';
        });
    } else if (guardianIs) {
        guardianFields.forEach(function(field) {
            field.style.display = 'none';
        });
    }
}

function getFieldValue(fieldId) {
    const field = document.getElementById(fieldId);
    return field ? field.value.trim() : '';
}

function validateForm() {
    const requiredFields = ['school', 'first_name', 'last_name', 'student_class', 'student_type'];
    let isValid = true;
    
    requiredFields.forEach(function(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field || !field.value) {
            if (field) field.classList.add('error');
            isValid = false;
        } else {
            if (field) field.classList.remove('error');
        }
    });
    
    if (window.billOnRegistration) {
        const account = document.getElementById('account');
        const paymentMethod = document.getElementById('payment_method');
        
        if (!account || !account.value) {
            if (account) account.classList.add('error');
            isValid = false;
        } else if (account) {
            account.classList.remove('error');
        }
        
        if (!paymentMethod || !paymentMethod.value) {
            if (paymentMethod) paymentMethod.classList.add('error');
            isValid = false;
        } else if (paymentMethod) {
            paymentMethod.classList.remove('error');
        }
    }
    
    return isValid;
}

function showError(message) {
    const errorDiv = document.getElementById('globalError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(function() {
            errorDiv.classList.remove('show');
        }, 5000);
    } else {
        alert(message);
    }
}

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
    const btnText = document.getElementById('btnText');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        if (btnText) btnText.innerHTML = '<span class="spinner"></span> Submitting...';
    }
    
    const formData = {
        school: getFieldValue('school'),
        first_name: getFieldValue('first_name'),
        second_name: getFieldValue('second_name'),
        last_name: getFieldValue('last_name'),
        date_of_birth: getFieldValue('date_of_birth'),
        gender: getFieldValue('gender'),
        student_phone_number: getFieldValue('student_phone_number'),
        student_class: getFieldValue('student_class'),
        section: getFieldValue('section'),
        student_type: getFieldValue('student_type'),
        religion: getFieldValue('religion'),
        date_of_admission: getFieldValue('date_of_admission'),
        national_identification_number: getFieldValue('national_identification_number'),
        local_identification_number: getFieldValue('local_identification_number'),
        previous_school_details: getFieldValue('previous_school_details'),
        medical_history: getFieldValue('medical_history'),
        portal_email: getFieldValue('portal_email'),
        father_name: getFieldValue('father_name'),
        mother_name: getFieldValue('mother_name'),
        phone_number: getFieldValue('phone_number'),
        mother_phone: getFieldValue('mother_phone'),
        father_email: getFieldValue('father_email'),
        mother_email: getFieldValue('mother_email'),
        father_occupation: getFieldValue('father_occupation'),
        mother_occupation: getFieldValue('mother_occupation'),
        if_guardian_is: getFieldValue('if_guardian_is'),
        guardian_name: getFieldValue('guardian_name'),
        guardian_relation: getFieldValue('guardian_relation'),
        guardian_phone: getFieldValue('guardian_phone'),
        guardian_email: getFieldValue('guardian_email'),
        guardian_occupation: getFieldValue('guardian_occupation'),
        guardian_address: getFieldValue('guardian_address'),
        current_address: getFieldValue('current_address'),
        permanent_address: getFieldValue('permanent_address'),
        account: getFieldValue('account'),
        payment_method: getFieldValue('payment_method')
    };
    
    try {
        const response = await frappe.call({
            method: 'school.www.student_registration.submit_registration',
            args: { data: JSON.stringify(formData) }
        });
        
        if (response.message && response.message.success) {
            document.querySelectorAll('.form-step').forEach(function(step) {
                step.style.display = 'none';
            });
            const successScreen = document.getElementById('successScreen');
            if (successScreen) {
                successScreen.classList.add('show');
                document.getElementById('successMsg').textContent = response.message.message;
                document.getElementById('refBadge').textContent = 'Reference: ' + response.message.name;
            }
        } else {
            showError(response.message?.message || 'Submission failed. Please try again.');
            if (submitBtn) {
                submitBtn.disabled = false;
                if (btnText) btnText.textContent = 'Submit Application';
            }
        }
    } catch (error) {
        console.error('Submission error:', error);
        showError('Network error. Please check your connection and try again.');
        if (submitBtn) {
            submitBtn.disabled = false;
            if (btnText) btnText.textContent = 'Submit Application';
        }
    }
    
    return false;
}

function buildReview() {
    const reviewContent = document.getElementById('reviewContent');
    if (!reviewContent) return;
    
    const fields = {
        'School': getFieldValue('school'),
        'Student Name': [getFieldValue('first_name'), getFieldValue('second_name'), getFieldValue('last_name')].filter(Boolean).join(' '),
        'Class': getFieldValue('student_class'),
        'Section': getFieldValue('section'),
        'Student Type': getFieldValue('student_type')
    };
    
    let html = '<table style="width:100%;border-collapse:collapse">';
    let i = 0;
    
    for (const [label, value] of Object.entries(fields)) {
        if (!value) continue;
        html += '<tr style="background:' + (i % 2 ? '#fff' : '#fdfbf7') + '">' +
                '<td style="padding:9px 14px;font-size:11px;font-weight:600;text-transform:uppercase;color:#7f8c8d;width:40%;border-bottom:1px solid #f9f5ee">' + escapeHtml(label) + '寿<td style="padding:9px 14px;font-size:14px;border-bottom:1px solid #f9f5ee">' + escapeHtml(value) + '寿\n                </tr>';
        i++;
    }
    
    html += '怎么办';
    reviewContent.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function goToStep(step) {
    const currentStep = document.querySelector('.form-step.active');
    const nextStep = document.getElementById('step' + step);
    
    if (currentStep && nextStep) {
        if (step > parseInt(currentStep.id.replace('step', '')) && !validateForm()) {
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
}

// Expose functions globally
window.loadAllClasses = loadAllClasses;
window.loadAllSections = loadAllSections;
window.toggleGuardianFields = toggleGuardianFields;
window.submitRegistration = submitRegistration;
window.goToStep = goToStep;
window.buildReview = buildReview;
window.validateForm = validateForm;