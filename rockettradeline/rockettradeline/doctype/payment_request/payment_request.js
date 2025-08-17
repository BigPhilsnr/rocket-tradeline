// Copyright (c) 2025, RocketTradeline and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Request', {
    refresh: function(frm) {
        // Add custom buttons based on status
        if (frm.doc.status === 'Pending') {
            frm.add_custom_button(__('Mark as Completed'), function() {
                mark_payment_completed(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Cancel Payment'), function() {
                cancel_payment(frm);
            }, __('Actions'));
        }
        
        if (frm.doc.status === 'Completed' && frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Verify Payment'), function() {
                verify_payment(frm);
            }, __('Actions'));
        }
        
        // Add button to view cart
        if (frm.doc.cart_id) {
            frm.add_custom_button(__('View Cart'), function() {
                frappe.set_route('Form', 'TradelineCart', frm.doc.cart_id);
            });
        }
        
        // Show payment status indicator
        set_status_indicator(frm);
        
        // Format payment data display
        format_payment_data(frm);
        
        // Check for expiry
        check_expiry(frm);
    },
    
    payment_method: function(frm) {
        // Load payment method configuration
        if (frm.doc.payment_method) {
            load_payment_config(frm);
        }
    },
    
    amount: function(frm) {
        calculate_fees(frm);
    }
});

function set_status_indicator(frm) {
    const status_colors = {
        'Draft': 'grey',
        'Pending': 'orange',
        'Completed': 'green',
        'Failed': 'red',
        'Expired': 'red',
        'Cancelled': 'red',
        'Verified': 'blue'
    };
    
    frm.dashboard.set_headline_alert(
        `<div class="indicator ${status_colors[frm.doc.status] || 'grey'}">
            ${frm.doc.status} Payment Request
        </div>`
    );
}

function format_payment_data(frm) {
    // Format payment data and response as JSON
    if (frm.doc.payment_data) {
        try {
            const data = JSON.parse(frm.doc.payment_data);
            frm.set_df_property('payment_data', 'description', 
                `<pre>${JSON.stringify(data, null, 2)}</pre>`);
        } catch (e) {
            // Invalid JSON, leave as is
        }
    }
    
    if (frm.doc.payment_response) {
        try {
            const response = JSON.parse(frm.doc.payment_response);
            frm.set_df_property('payment_response', 'description', 
                `<pre>${JSON.stringify(response, null, 2)}</pre>`);
        } catch (e) {
            // Invalid JSON, leave as is
        }
    }
}

function check_expiry(frm) {
    if (frm.doc.expiry_date && frm.doc.status === 'Pending') {
        const now = new Date();
        const expiry = new Date(frm.doc.expiry_date);
        
        if (expiry < now) {
            frm.dashboard.add_comment_section();
            frm.dashboard.show_progress('Expired', 'This payment request has expired', 'red');
        } else {
            const hours_left = Math.round((expiry - now) / (1000 * 60 * 60));
            if (hours_left < 2) {
                frm.dashboard.show_progress('Expiring Soon', 
                    `This payment request expires in ${hours_left} hour(s)`, 'orange');
            }
        }
    }
}

function load_payment_config(frm) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Payment Configuration',
            filters: {
                payment_method: frm.doc.payment_method,
                is_active: 1
            }
        },
        callback: function(r) {
            if (r.message) {
                const config = r.message;
                if (config.instructions) {
                    frm.set_value('instructions', config.instructions);
                }
            }
        }
    });
}

function calculate_fees(frm) {
    if (frm.doc.amount && frm.doc.payment_method) {
        frappe.call({
            method: 'rockettradeline.api.payment.calculate_payment_fees',
            args: {
                amount: frm.doc.amount,
                payment_method: frm.doc.payment_method
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frm.set_value('fees', r.message.fees.total_fee);
                    frm.set_value('total_amount', r.message.total_amount);
                }
            }
        });
    }
}

function mark_payment_completed(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Mark Payment as Completed'),
        fields: [
            {
                fieldname: 'transaction_id',
                fieldtype: 'Data',
                label: __('Transaction ID'),
                reqd: 1
            },
            {
                fieldname: 'payment_notes',
                fieldtype: 'Text',
                label: __('Payment Notes')
            }
        ],
        primary_action: function() {
            const values = dialog.get_values();
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Payment Request',
                    name: frm.doc.name,
                    fieldname: {
                        status: 'Completed',
                        transaction_id: values.transaction_id,
                        completed_at: frappe.datetime.now_datetime()
                    }
                },
                callback: function(r) {
                    if (values.payment_notes) {
                        frm.add_comment('Comment', values.payment_notes);
                    }
                    frm.refresh();
                    frappe.msgprint(__('Payment marked as completed'));
                    dialog.hide();
                }
            });
        },
        primary_action_label: __('Mark Completed')
    });
    
    dialog.show();
}

function cancel_payment(frm) {
    frappe.confirm(
        __('Are you sure you want to cancel this payment request?'),
        function() {
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Payment Request',
                    name: frm.doc.name,
                    fieldname: 'status',
                    value: 'Cancelled'
                },
                callback: function(r) {
                    frm.refresh();
                    frappe.msgprint(__('Payment request cancelled'));
                }
            });
        }
    );
}

function verify_payment(frm) {
    frappe.call({
        method: 'rockettradeline.api.payment.verify_payment',
        args: {
            payment_request_id: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.refresh();
                frappe.msgprint({
                    title: __('Payment Verified'),
                    message: r.message.message,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Verification Failed'),
                    message: r.message ? r.message.error : 'Unknown error',
                    indicator: 'red'
                });
            }
        }
    });
}

// Auto-refresh form every 30 seconds for pending payments
frappe.ui.form.on('Payment Request', {
    onload: function(frm) {
        if (frm.doc.status === 'Pending') {
            frm.auto_refresh_interval = setInterval(function() {
                if (!frm.is_dirty()) {
                    frm.refresh();
                }
            }, 30000); // 30 seconds
        }
    },
    
    before_unload: function(frm) {
        if (frm.auto_refresh_interval) {
            clearInterval(frm.auto_refresh_interval);
        }
    }
});
