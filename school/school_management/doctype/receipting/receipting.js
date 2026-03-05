// ─────────────────────────────────────────────────────────────
//  RECEIPTING — Main Form
// ─────────────────────────────────────────────────────────────
frappe.ui.form.on('Receipting', {

    onload: function(frm) {
        if (frm.doc.__islocal) {
            frm.trigger('fetch_default_account');
        }
        frm.trigger('set_account_query');
        // Ensure account field is always visible
        frm.set_df_property('account', 'hidden', 0);
        if (frm.doc.account) frm.trigger('account');
        setTimeout(function() { setup_student_search(frm); }, 800);
    },

    refresh: function(frm) {
        frm.trigger('set_account_query');
        // Ensure account field is always visible
        frm.set_df_property('account', 'hidden', 0);
        if (frm.doc.account_currency) toggle_currency_fields(frm);

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button('Auto Distribute', function() {
                auto_distribute(frm);
            }).addClass('btn-primary');
        }
        setTimeout(function() { setup_student_search(frm); }, 600);
    },

    // ── Payment Method ────────────────────────────────────────
    payment_method: function(frm) {
        frm.set_value('account', '');
        frm.doc.account_currency = '';
        frm.set_value('exchange_rate', 1);
        toggle_currency_fields(frm);
        frm.trigger('set_account_query');
        frm.trigger('fetch_default_account');
        // Re-show account field after method change
        frm.set_df_property('account', 'hidden', 0);
    },

    set_account_query: function(frm) {
        // Always show Bank + Cash — identical to Payment Entry filter
        frm.set_query('account', function() {
            return {
                filters: [
                    ['Account', 'account_type', 'in', ['Bank', 'Cash']],
                    ['Account', 'is_group',     '=',  0],
                    ['Account', 'company',      '=',  frappe.defaults.get_default('company')]
                ]
            };
        });
    },

    fetch_default_account: function(frm) {
        let account_type = (frm.doc.payment_method === 'Cash') ? 'Cash' : 'Bank';
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Account',
                filters: [
                    ['account_type', '=', account_type],
                    ['is_group',     '=', 0],
                    ['company',      '=', frappe.defaults.get_default('company')]
                ],
                fields: ['name'],
                limit: 1
            },
            callback: function(r) {
                if (r.message && r.message.length) {
                    frm.set_value('account', r.message[0].name);
                    frm.set_df_property('account', 'hidden', 0);
                }
            }
        });
    },

    date: function(frm) {
        if (frm.doc.account) frm.trigger('account');
    },

    account: function(frm) {
        frm.trigger('set_account_query');
        if (!frm.doc.account) {
            frm.doc.account_currency = '';
            frm.set_value('exchange_rate', 1);
            toggle_currency_fields(frm);
            return;
        }
        frappe.db.get_value('Account', frm.doc.account, 'account_currency', function(r) {
            if (!r || !r.account_currency) return;
            let company_currency = frappe.boot.sysdefaults.currency;
            let acct_currency    = r.account_currency;

            frm.doc.account_currency = acct_currency;
            frm.get_field('account_currency').set_input(acct_currency);
            frm.refresh_field('account_currency');

            if (acct_currency !== company_currency) {
                frappe.call({
                    method: 'erpnext.setup.utils.get_exchange_rate',
                    args: {
                        transaction_date: frm.doc.date || frappe.datetime.get_today(),
                        from_currency:    acct_currency,
                        to_currency:      company_currency,
                        args:             'for_buying'
                    },
                    callback: function(res) {
                        frm.set_value('exchange_rate', res.message || 1);
                        if (!res.message) frappe.msgprint(__('No exchange rate found. Please enter manually.'));
                        toggle_currency_fields(frm);
                    }
                });
            } else {
                frm.set_value('exchange_rate', 1);
                toggle_currency_fields(frm);
            }
        });
    },

    // ── Amounts ───────────────────────────────────────────────
    // Rule: whichever field the user typed in drives the other.
    // We NEVER use frm.set_value for the calculated side — that fires
    // the target field's own event and creates a loop. Instead we write
    // directly to frm.doc and call refresh_field (display only, no event).

    paid_amount: function(frm) {
        if (frm._paid_updating) return;
        frm._paid_updating = true;
        let rate = flt(frm.doc.exchange_rate) || 1;
        let received = is_multi_currency(frm)
            ? flt(frm.doc.paid_amount / rate, 2)
            : frm.doc.paid_amount;
        // Write directly — no event fired, no loop
        frm.doc.received_amount = received;
        frm.refresh_field('received_amount');
        frm._paid_updating = false;
        update_rate_description(frm);
        auto_distribute(frm);
    },

    received_amount: function(frm) {
        if (frm._paid_updating) return;
        if (!is_multi_currency(frm)) return;
        frm._paid_updating = true;
        let rate = flt(frm.doc.exchange_rate) || 1;
        // Write directly — no event fired, no loop
        frm.doc.paid_amount = flt(frm.doc.received_amount * rate, 2);
        frm.refresh_field('paid_amount');
        frm._paid_updating = false;
        update_rate_description(frm);
        auto_distribute(frm);
    },

    exchange_rate: function(frm) {
        if (!is_multi_currency(frm)) return;
        let rate = flt(frm.doc.exchange_rate) || 1;
        frm._paid_updating = true;
        // Exchange rate changed: recalculate received from paid (paid is the source of truth)
        frm.doc.received_amount = flt(frm.doc.paid_amount / rate, 2);
        frm.refresh_field('received_amount');
        frm._paid_updating = false;
        update_rate_description(frm);
        recalculate_invoice_allocations(frm);
    },

    // ── Student Class / Section ───────────────────────────────
    student_class: function(frm) {
        frm.set_value('student_name', '');
        frm.set_value('student_display_name', '');
        frm.set_value('section', '');
        frm.clear_table('invoices');
        frm.refresh_field('invoices');
        calculate_totals(frm);
        set_section_filter(frm);
        $('#student-search-input').val('');
        setTimeout(function() { setup_student_search(frm); }, 600);
    },

    section: function(frm) {
        frm.set_value('student_name', '');
        frm.set_value('student_display_name', '');
        frm.clear_table('invoices');
        frm.refresh_field('invoices');
        calculate_totals(frm);
        $('#student-search-input').val('');
        setTimeout(function() { setup_student_search(frm); }, 600);
    }
});

// ─────────────────────────────────────────────────────────────
//  RECEIPT ITEM — Child Table
// ─────────────────────────────────────────────────────────────
frappe.ui.form.on('Receipt Item', {
    allocated: function(frm, cdt, cdn) {
        if (frm._alloc_updating) return;
        frm._alloc_updating = true;
        let row  = locals[cdt][cdn];
        let rate = flt(frm.doc.exchange_rate) || 1;
        if (is_multi_currency(frm)) {
            frappe.model.set_value(cdt, cdn, 'allocated_foreign', flt(row.allocated / rate, 2));
        }
        frm._alloc_updating = false;
        calculate_totals(frm);
    },

    allocated_foreign: function(frm, cdt, cdn) {
        if (!is_multi_currency(frm)) return;
        if (frm._alloc_updating) return;
        frm._alloc_updating = true;
        let row  = locals[cdt][cdn];
        let rate = flt(frm.doc.exchange_rate) || 1;
        frappe.model.set_value(cdt, cdn, 'allocated', flt(row.allocated_foreign * rate, 2));
        frm._alloc_updating = false;
        calculate_totals(frm);
    },

    invoice_number: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.invoice_number) return;
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Sales Invoice', name: row.invoice_number },
            callback: function(r) {
                if (!r.message) return;
                frappe.model.set_value(cdt, cdn, 'fees_structure',    r.message.fees_structure || '');
                frappe.model.set_value(cdt, cdn, 'total',             r.message.grand_total);
                frappe.model.set_value(cdt, cdn, 'outstanding',       r.message.outstanding_amount);
                frappe.model.set_value(cdt, cdn, 'allocated',         0);
                frappe.model.set_value(cdt, cdn, 'allocated_foreign', 0);
            }
        });
    }
});

// ─────────────────────────────────────────────────────────────
//  STUDENT SEARCH — Replaces native link field with plain input
//  The Frappe link widget resets its value on blur unless the selection
//  came from its own internal list. By hiding it and using our own
//  plain <input>, we bypass that reset entirely — one click always sticks.
// ─────────────────────────────────────────────────────────────
function setup_student_search(frm) {
    let field = frm.get_field('student_name');
    if (!field || !field.$wrapper) return;

    // Hide the native Frappe link input + awesomplete container
    field.$wrapper.find('input:not(#student-search-input)').hide();
    field.$wrapper.find('.awesomplete').hide();
    field.$wrapper.find('.link-btn').hide();

    // Inject our plain search input once
    if (!field.$wrapper.find('#student-search-input').length) {
        let $s = $('<input id="student-search-input" type="text" autocomplete="off">')
            .attr('placeholder', 'Type student name or ID...')
            .css({
                width:        '100%',
                padding:      '6px 10px',
                border:       '1px solid #d1d8dd',
                borderRadius: '4px',
                fontSize:     '13px',
                boxSizing:    'border-box',
                background:   '#fff',
                display:      'block'
            });
        field.$wrapper.append($s);
    }

    let $input = field.$wrapper.find('#student-search-input');

    // Pre-fill on saved doc reload
    if (frm.doc.student_name && !$input.val()) {
        $input.val(frm.doc.student_display_name || frm.doc.student_name);
    }

    // Remove stale listeners
    $input.off('.sdd');
    $(document).off('.sdd_out');
    $('#student-search-dd').remove();

    // ── Dropdown ──────────────────────────────────────────────
    function show_dropdown(txt) {
        frappe.call({
            method: 'school.school_management.doctype.receipting.receipting.search_students',
            args: {
                doctype:     'Student',
                txt:         txt || '',
                searchfield: 'name',
                start:       0,
                page_len:    20,
                filters: {
                    student_class: frm.doc.student_class || '',
                    section:       frm.doc.section || ''
                }
            },
            callback: function(r) {
                $('#student-search-dd').remove();
                if (!r.message || !r.message.length) return;

                let rect  = $input[0].getBoundingClientRect();
                let $list = $('<ul id="student-search-dd"></ul>').css({
                    position:   'fixed',
                    top:        rect.bottom + 2,
                    left:       rect.left,
                    width:      Math.max(rect.width, 280),
                    background: '#fff',
                    border:     '1px solid #d1d8dd',
                    borderRadius: '6px',
                    zIndex:     100000,
                    listStyle:  'none',
                    padding:    '4px 0',
                    margin:     0,
                    maxHeight:  '260px',
                    overflowY:  'auto',
                    boxShadow:  '0 8px 20px rgba(0,0,0,0.15)'
                });

                r.message.forEach(function(s) {
                    let reg      = s[0];
                    let fullname = (s[1] || '').trim().replace(/\s+/g, ' ');
                    let label    = reg + ' — ' + fullname;

                    $('<li></li>').text(label).css({
                        padding:      '9px 14px',
                        cursor:       'pointer',
                        fontSize:     '13px',
                        color:        '#333',
                        borderBottom: '1px solid #f0f0f0'
                    })
                    .hover(
                        function() { $(this).css({ background: '#f0f4ff', color: '#1a73e8' }); },
                        function() { $(this).css({ background: '#fff',    color: '#333' }); }
                    )
                    // mousedown fires BEFORE blur — one click, always sticks
                    .mousedown(function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        $('#student-search-dd').remove();

                        // 1. Show label in our input immediately
                        $input.val(label);

                        // 2. Write directly to doc — bypasses Frappe link widget entirely
                        frm.doc.student_name = reg;

                        // 3. DO NOT call frm.refresh_field or frm.set_value here —
                        //    both re-render the Frappe field and wipe frm.doc.student_name.
                        //    Instead, mark dirty so Frappe knows the doc changed.
                        frm.dirty();

                        // 4. Load invoices — pass reg directly, never reads frm.doc.student_name
                        load_student_invoices(frm, reg);
                    })
                    .appendTo($list);
                });

                $('body').append($list);

                $(document).off('.sdd_out').on('mousedown.sdd_out', function(e) {
                    if (!$(e.target).closest('#student-search-dd, #student-search-input').length) {
                        $('#student-search-dd').remove();
                    }
                });
            }
        });
    }

    $input.on('focus.sdd', function() {
        show_dropdown($input.val());
    });

    $input.on('keyup.sdd', function(e) {
        if ([9, 13, 16, 17, 18, 27, 37, 38, 39, 40].indexOf(e.which) > -1) {
            if (e.which === 27) $('#student-search-dd').remove();
            return;
        }
        show_dropdown($input.val());
    });

    $input.on('blur.sdd', function() {
        setTimeout(function() { $('#student-search-dd').remove(); }, 250);
    });
}

// ─────────────────────────────────────────────────────────────
//  LOAD STUDENT INVOICES
// ─────────────────────────────────────────────────────────────
function load_student_invoices(frm, student_name) {
    student_name = student_name || frm.doc.student_name;
    if (!student_name) return;

    // Get display name + auto-fill class/section
    // Use frm.doc directly to avoid set_value re-renders wiping student_name
    frappe.db.get_value(
        'Student', student_name,
        ['first_name', 'second_name', 'last_name', 'full_name', 'student_class', 'section'],
        function(r) {
            if (!r) return;
            let display = (r.full_name && r.full_name.trim())
                ? r.full_name.trim()
                : [r.first_name, r.second_name, r.last_name]
                    .filter(function(v) { return v && v.trim(); }).join(' ');
            // Write to doc directly — avoids triggering field refresh cascade
            frm.doc.student_name         = student_name;  // re-pin in case anything reset it
            frm.doc.student_display_name = display || student_name;
            frm.refresh_field('student_display_name');
            if (!frm.doc.student_class && r.student_class) {
                frm.doc.student_class = r.student_class;
                frm.refresh_field('student_class');
            }
            if (!frm.doc.section && r.section) {
                frm.doc.section = r.section;
                frm.refresh_field('section');
            }
            set_section_filter(frm);
            frm.dirty();
        }
    );

    // Fetch outstanding invoices via server method (handles custom field permissions)
    frappe.call({
        method: 'school.school_management.doctype.receipting.receipting.get_outstanding_invoices',
        args: { student_name: student_name },
        callback: function(r) {
            frm.clear_table('invoices');
            if (r.message && r.message.length) {
                r.message.forEach(function(inv) {
                    let row               = frm.add_child('invoices');
                    row.invoice_number    = inv.name;
                    row.fees_structure    = inv.fees_structure || '';
                    row.total             = inv.grand_total;
                    row.outstanding       = inv.outstanding_amount;
                    row.allocated         = 0;
                    row.allocated_foreign = 0;
                });
                frm.refresh_field('invoices');
                toggle_currency_fields(frm);
                calculate_totals(frm);
                frappe.show_alert({ message: r.message.length + ' invoice(s) loaded', indicator: 'green' });
                if (flt(frm.doc.paid_amount) > 0) auto_distribute(frm);
            } else {
                frappe.show_alert({ message: 'No outstanding invoices for this student.', indicator: 'orange' });
                calculate_totals(frm);
            }
        }
    });
}

// ─────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────

function auto_distribute(frm) {
    let paid = flt(frm.doc.paid_amount);
    if (!paid || paid <= 0) return;
    let remaining = paid;
    (frm.doc.invoices || []).forEach(function(row) {
        let allocate = 0;
        if (remaining > 0) {
            allocate  = Math.min(remaining, flt(row.outstanding));
            remaining = flt(remaining - allocate);
        }
        frappe.model.set_value(row.doctype, row.name, 'allocated', flt(allocate, 2));
        if (is_multi_currency(frm)) {
            let rate = flt(frm.doc.exchange_rate) || 1;
            frappe.model.set_value(row.doctype, row.name, 'allocated_foreign', flt(allocate / rate, 2));
        }
    });
    frm.refresh_field('invoices');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    // NOTE: total_allocated field does not exist in the DocType — do not reference it.
    let total = 0, outstanding = 0;
    (frm.doc.invoices || []).forEach(function(row) {
        total       += flt(row.total);
        outstanding += flt(row.outstanding);
    });
    frm.set_value('total_amount',      flt(total, 2));
    frm.set_value('total_outstanding', flt(outstanding, 2));
}

function set_section_filter(frm) {
    frm.set_query('section', function() {
        if (!frm.doc.student_class) return {};
        return { filters: { student_class: frm.doc.student_class } };
    });
}

function recalculate_invoice_allocations(frm) {
    if (!is_multi_currency(frm)) return;
    let rate = flt(frm.doc.exchange_rate) || 1;
    (frm.doc.invoices || []).forEach(function(row) {
        if (flt(row.allocated) > 0) {
            frappe.model.set_value(row.doctype, row.name, 'allocated_foreign', flt(row.allocated / rate, 2));
        }
    });
    frm.refresh_field('invoices');
}

function toggle_currency_fields(frm) {
    let multi            = is_multi_currency(frm);
    let company_currency = frappe.boot.sysdefaults.currency;
    let account_currency = frm.doc.account_currency || company_currency;

    frm.set_df_property('exchange_rate',   'hidden', multi ? 0 : 1);
    frm.set_df_property('received_amount', 'hidden', multi ? 0 : 1);

    // account field must always remain visible — never hide it
    frm.set_df_property('account', 'hidden', 0);

    if (frm.fields_dict['invoices'] && frm.fields_dict['invoices'].grid) {
        frm.fields_dict['invoices'].grid.update_docfield_property('allocated_foreign', 'hidden', multi ? 0 : 1);
        frm.fields_dict['invoices'].grid.update_docfield_property(
            'allocated', 'label', 'Allocated (' + (multi ? company_currency : account_currency) + ')'
        );
        if (multi) {
            frm.fields_dict['invoices'].grid.update_docfield_property(
                'allocated_foreign', 'label', 'Allocated (' + account_currency + ')'
            );
        }
    }

    frm.set_df_property('paid_amount', 'label',
        'Paid Amount (' + (multi ? company_currency : account_currency) + ')'
    );
    if (multi) {
        frm.set_df_property('received_amount', 'label', 'Received Amount (' + account_currency + ')');
    }

    update_rate_description(frm);
    frm.refresh_fields(['paid_amount', 'exchange_rate', 'received_amount', 'account_currency']);
    frm.refresh_field('invoices');
}

function update_rate_description(frm) {
    if (!is_multi_currency(frm)) {
        frm.set_df_property('exchange_rate', 'description', '');
        frm.refresh_field('exchange_rate');
        return;
    }
    let rate = flt(frm.doc.exchange_rate, 4);
    frm.set_df_property('exchange_rate', 'description',
        '1 ' + frm.doc.account_currency + ' = ' + rate + ' ' + frappe.boot.sysdefaults.currency
    );
    frm.refresh_field('exchange_rate');
}

function is_multi_currency(frm) {
    let acct = frm.doc.account_currency;
    return !!(acct && acct !== frappe.boot.sysdefaults.currency);
}

function flt(val, precision) {
    precision = (precision !== undefined) ? precision : 9;
    return parseFloat((parseFloat(val) || 0).toFixed(precision));
}