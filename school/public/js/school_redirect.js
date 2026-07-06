(function () {

    /* ─────────────────────────────────────────────────────────────────────
       1.  Intercept the "School Management" sidebar link → admin portal
    ───────────────────────────────────────────────────────────────────── */
    function interceptSchoolManagement() {
        if (typeof frappe === 'undefined') return;

        var links = document.querySelectorAll('.item-anchor');
        links.forEach(function (link) {
            var label = link.querySelector('.sidebar-item-label');
            if (label && label.textContent.trim() === 'School Management') {
                var newLink = link.cloneNode(true);
                link.parentNode.replaceChild(newLink, link);
                newLink.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.location.href = '/assets/school/html/admin_school_management.html';
                });
            }
        });
    }

    /* ─────────────────────────────────────────────────────────────────────
       2.  Inject a floating "Home" button for teachers
           - Only shown inside /app/* pages (ERPNext backend)
           - Only shown for users who have a Teacher record
           - Clicking it goes to the Teacher Portal
           - A small "×" allows them to hide it for the session
    ───────────────────────────────────────────────────────────────────── */
    var HOME_BTN_ID = 'school-teacher-home-btn';
    var DISMISS_KEY = 'school_home_btn_dismissed';

    function injectTeacherHomeButton() {
        // Only inject on /app pages
        if (!window.location.pathname.startsWith('/app')) return;
        // Don't double-inject
        if (document.getElementById(HOME_BTN_ID)) return;
        // Don't show if user dismissed it this session
        if (sessionStorage.getItem(DISMISS_KEY)) return;

        var btn = document.createElement('div');
        btn.id = HOME_BTN_ID;
        btn.innerHTML =
            '<a id="school-home-link" href="/assets/school/html/teacher-portal.html" ' +
            'title="Go to Teacher Dashboard" style="' +
            'display:inline-flex;align-items:center;gap:8px;' +
            'background:linear-gradient(135deg,#1e3a5f,#2e86de);' +
            'color:white;text-decoration:none;border-radius:12px 0 0 12px;' +
            'padding:10px 16px 10px 14px;font-size:13px;font-weight:600;' +
            'box-shadow:0 4px 16px rgba(30,58,95,.35);' +
            'transition:all .2s;white-space:nowrap;">' +
            '<span style="font-size:18px;line-height:1;">🏠</span>' +
            '<span>Teacher Dashboard</span>' +
            '</a>' +
            '<button id="school-home-dismiss" title="Hide" style="' +
            'background:#1e3a5f;border:none;color:rgba(255,255,255,.75);' +
            'cursor:pointer;font-size:14px;padding:10px 10px;' +
            'border-radius:0 12px 12px 0;' +
            'box-shadow:0 4px 16px rgba(30,58,95,.35);' +
            'transition:color .2s;">×</button>';

        Object.assign(btn.style, {
            position: 'fixed',
            bottom: '28px',
            right: '0',
            zIndex: '99999',
            display: 'flex',
            alignItems: 'stretch',
            opacity: '0',
            transform: 'translateX(20px)',
            transition: 'opacity .4s ease, transform .4s ease'
        });

        document.body.appendChild(btn);

        // Animate in
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                btn.style.opacity = '1';
                btn.style.transform = 'translateX(0)';
            });
        });

        // Hover effect on the link
        var link = document.getElementById('school-home-link');
        link.addEventListener('mouseenter', function () {
            this.style.background = 'linear-gradient(135deg,#2e86de,#1e3a5f)';
            this.style.paddingRight = '20px';
        });
        link.addEventListener('mouseleave', function () {
            this.style.background = 'linear-gradient(135deg,#1e3a5f,#2e86de)';
            this.style.paddingRight = '16px';
        });

        // Dismiss button
        document.getElementById('school-home-dismiss').addEventListener('click', function () {
            btn.style.opacity = '0';
            btn.style.transform = 'translateX(20px)';
            sessionStorage.setItem(DISMISS_KEY, '1');
            setTimeout(function () { btn.remove(); }, 400);
        });
    }

    function checkAndInjectForTeacher() {
        if (typeof frappe === 'undefined' || !frappe.session || !frappe.session.user) return;
        var user = frappe.session.user;
        if (!user || user === 'Guest' || user === 'Administrator') return;

        // Check if this user is a teacher (cached in sessionStorage)
        var cacheKey = 'school_is_teacher_' + user;
        var cached = sessionStorage.getItem(cacheKey);
        if (cached === 'yes') {
            injectTeacherHomeButton();
            return;
        }
        if (cached === 'no') return;

        // Ask Frappe if a Teacher record exists for this email
        frappe.call({
            method: 'frappe.client.get_count',
            args: {
                doctype: 'Teacher',
                filters: [['portal_email', '=', user]]
            },
            callback: function (r) {
                var isTeacher = r.message && r.message > 0;
                sessionStorage.setItem(cacheKey, isTeacher ? 'yes' : 'no');
                if (isTeacher) injectTeacherHomeButton();
            }
        });
    }

    /* ─────────────────────────────────────────────────────────────────────
       3.  Boot – run after Frappe is ready
    ───────────────────────────────────────────────────────────────────── */
    $(document).ready(function () {
        // Sidebar intercept
        setTimeout(interceptSchoolManagement, 500);
        setTimeout(interceptSchoolManagement, 1000);
        setTimeout(interceptSchoolManagement, 2000);

        // Teacher home button (slight delay to let frappe.session populate)
        setTimeout(checkAndInjectForTeacher, 1200);

        // Check for missing term
        setTimeout(function() {
            if (frappe.boot && frappe.boot.missing_active_term && frappe.session && frappe.session.user !== "Guest") {
                var userRoles = frappe.user.get_roles();
                if (userRoles.includes("System Manager") || userRoles.includes("Administrator") || userRoles.includes("School User")) {
                    frappe.msgprint({
                        title: __('Missing Active Term'),
                        indicator: 'orange',
                        message: __('There is no active term set for today. Please go to the <a href="/app/term">Term</a> list and set the current term.')
                    });
                }
            }
        }, 1500);

        // Re-run on every route change (SPA navigation)
        if (typeof frappe !== 'undefined' && frappe.router) {
            frappe.router.on('change', function () {
                setTimeout(interceptSchoolManagement, 500);
                // Re-inject button if it was removed by SPA navigation
                setTimeout(function () {
                    if (!document.getElementById(HOME_BTN_ID) && !sessionStorage.getItem(DISMISS_KEY)) {
                        checkAndInjectForTeacher();
                    }
                }, 800);
            });
        }
    });

})();


/* ─────────────────────────────────────────────────────────────────────────
   Student DocType client-side logic
──────────────────────────────────────────────────────────────────────────*/
frappe.ui.form.on('Student', {
    refresh: function (frm) {
        if (!frm.doc.school) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: { name: frappe.session.user },
                    fieldname: "school"
                },
                callback: function (r) {
                    if (r.message && r.message.school) {
                        frm.set_value("school", r.message.school);
                    }
                }
            });
        }

        frm.set_query("account", function () {
            return {
                filters: {
                    is_group: 0,
                    company: frappe.defaults.get_default("company"),
                    account_type: ["in", ["Bank", "Cash"]]
                }
            };
        });

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "School Settings", name: "School Settings" },
            callback: function (r) {
                if (r.message && r.message.enable_registration_billing) {
                    frm.set_df_property("billed_on_registration", "read_only", 1);
                }
            }
        });
    },

    admin_fee_paid: function (frm) {
        if (frm.doc.admin_fee_paid && !frm.doc.admin_fees_structure) {
            frappe.msgprint(__("Please select an Admin Fees Structure before marking as Paid."));
            frm.set_value("admin_fee_paid", 0);
        }
    },

    student_type: function (frm) {
        if (!frm.doc.student_type) return;

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "School Settings", name: "School Settings" },
            callback: function (r) {
                if (!r.message) return;
                var settings = r.message;

                var adminRows = settings.fee_structure_defaults || [];
                var adminMatch = adminRows.find(function (row) { return row.status === frm.doc.student_type; });
                if (adminMatch) {
                    frm.set_value("paying_admin_fee", 1);
                    frm.set_value("admin_fees_structure", adminMatch.fees_structure);
                    frappe.show_alert({
                        message: __("Admin fees structure auto-set for " + frm.doc.student_type),
                        indicator: "green"
                    }, 4);
                }

                if (settings.enable_registration_billing) {
                    var regRows = settings.registration_billing_defaults || [];
                    var regMatch = regRows.find(function (row) { return row.status === frm.doc.student_type; });
                    if (regMatch) {
                        frm.set_value("fees_structure", regMatch.fees_structure);
                        frm.set_value("billed_on_registration", 1);
                        frm.set_df_property("billed_on_registration", "read_only", 1);
                        frappe.show_alert({
                            message: __("Billing fees structure auto-set for " + frm.doc.student_type),
                            indicator: "green"
                        }, 4);
                    } else {
                        frappe.show_alert({
                            message: __("No registration billing found in Settings for: " + frm.doc.student_type),
                            indicator: "orange"
                        }, 4);
                    }
                }
            }
        });
    }
});
