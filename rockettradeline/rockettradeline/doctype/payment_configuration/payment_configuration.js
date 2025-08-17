// Copyright (c) 2025, RocketTradeline and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Configuration', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Test Configuration'), function() {
                test_payment_configuration(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Create Sample Payment'), function() {
                create_sample_payment(frm);
            }, __('Actions'));
        }
        
        // Set payment method icons
        set_payment_method_icon(frm);
        
        // Show/hide fields based on payment method
        toggle_payment_fields(frm);
    },
    
    payment_method: function(frm) {
        set_payment_method_icon(frm);
        toggle_payment_fields(frm);
        set_default_values(frm);
    },
    
    min_amount: function(frm) {
        validate_amount_limits(frm);
    },
    
    max_amount: function(frm) {
        validate_amount_limits(frm);
    },
    
    percentage_fee: function(frm) {
        if (frm.doc.percentage_fee > 100) {
            frappe.msgprint(__('Percentage fee cannot exceed 100%'));
            frm.set_value('percentage_fee', 0);
        }
    }
});

function set_payment_method_icon(frm) {
    const icons = {
        'Apple Cash': 'fa-apple',
        'Zelle': 'fa-university',
        'CashApp': 'fa-dollar-sign',
        'Venmo': 'fa-mobile',
        'PayPal': 'fa-paypal',
        'Credit Card': 'fa-credit-card',
        'Bank Transfer': 'fa-bank',
        'Cryptocurrency': 'fa-bitcoin'
    };
    
    if (frm.doc.payment_method && !frm.doc.icon) {
        frm.set_value('icon', icons[frm.doc.payment_method] || 'fa-money');
    }
}

function toggle_payment_fields(frm) {
    const method = frm.doc.payment_method;
    
    // Show/hide API configuration section
    frm.toggle_display('api_configuration', method === 'PayPal');
    
    // Show/hide specific account fields
    frm.toggle_display('account_email', ['Zelle', 'CashApp', 'Venmo', 'PayPal'].includes(method));
    frm.toggle_display('phone_number', ['Apple Cash', 'Zelle', 'CashApp', 'Venmo'].includes(method));
    frm.toggle_display('account_id', ['CashApp', 'Venmo'].includes(method));
    
    // Set field requirements
    frm.toggle_reqd('phone_number', method === 'Apple Cash');
    frm.toggle_reqd('api_key', method === 'PayPal' && !frm.doc.sandbox_mode);
    frm.toggle_reqd('api_secret', method === 'PayPal' && !frm.doc.sandbox_mode);
}

function set_default_values(frm) {
    const defaults = {
        'Apple Cash': {
            payment_type: 'Digital Wallet',
            min_amount: 1,
            max_amount: 3000,
            fixed_fee: 0,
            percentage_fee: 0,
            instructions: 'Send payment via Apple Cash to the provided phone number'
        },
        'Zelle': {
            payment_type: 'Bank Transfer',
            min_amount: 1,
            max_amount: 2500,
            fixed_fee: 0,
            percentage_fee: 0,
            instructions: 'Send payment via Zelle using the provided email or phone number'
        },
        'CashApp': {
            payment_type: 'Peer-to-Peer',
            min_amount: 1,
            max_amount: 2500,
            fixed_fee: 0,
            percentage_fee: 2.9,
            instructions: 'Send payment via Cash App to the provided username or phone'
        },
        'Venmo': {
            payment_type: 'Peer-to-Peer',
            min_amount: 0.01,
            max_amount: 4999.99,
            fixed_fee: 0,
            percentage_fee: 1.9,
            instructions: 'Send payment via Venmo to the provided username'
        },
        'PayPal': {
            payment_type: 'Digital Wallet',
            min_amount: 0.01,
            max_amount: 10000,
            fixed_fee: 0.30,
            percentage_fee: 3.49,
            instructions: 'Complete payment using the PayPal checkout link'
        }
    };
    
    const method = frm.doc.payment_method;
    if (method && defaults[method] && frm.doc.__islocal) {
        Object.keys(defaults[method]).forEach(field => {
            if (!frm.doc[field]) {
                frm.set_value(field, defaults[method][field]);
            }
        });
    }
}

function validate_amount_limits(frm) {
    if (frm.doc.min_amount >= frm.doc.max_amount) {
        frappe.msgprint(__('Minimum amount must be less than maximum amount'));
        return false;
    }
    return true;
}

function test_payment_configuration(frm) {
    frappe.call({
        method: 'rockettradeline.api.payment.test_payment_configuration',
        args: {
            payment_method: frm.doc.payment_method,
            test_amount: 100
        },
        callback: function(r) {
            if (r.message.success) {
                frappe.msgprint({
                    title: __('Configuration Test Successful'),
                    message: r.message.message,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Configuration Test Failed'),
                    message: r.message.error,
                    indicator: 'red'
                });
            }
        }
    });
}

function create_sample_payment(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Sample Payment'),
        fields: [
            {
                fieldname: 'amount',
                fieldtype: 'Currency',
                label: __('Amount'),
                reqd: 1,
                default: 100
            },
            {
                fieldname: 'customer_email',
                fieldtype: 'Data',
                label: __('Customer Email'),
                default: 'test@example.com'
            }
        ],
        primary_action: function() {
            const values = dialog.get_values();
            frappe.call({
                method: 'rockettradeline.api.payment.create_sample_payment',
                args: {
                    payment_method: frm.doc.payment_method,
                    amount: values.amount,
                    customer_email: values.customer_email
                },
                callback: function(r) {
                    if (r.message.success) {
                        frappe.msgprint({
                            title: __('Sample Payment Created'),
                            message: `<pre>${JSON.stringify(r.message.payment_request, null, 2)}</pre>`,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Sample Payment Failed'),
                            message: r.message.error,
                            indicator: 'red'
                        });
                    }
                    dialog.hide();
                }
            });
        },
        primary_action_label: __('Create Payment')
    });
    
    dialog.show();
}

// Add custom styling for payment method icons
frappe.ui.form.on('Payment Configuration', {
    onload: function(frm) {
        // Add CSS for payment method styling
        if (!$('#payment-config-styles').length) {
            $('<style id="payment-config-styles">')
                .text(`
                    .payment-method-icon {
                        font-size: 1.2em;
                        margin-right: 8px;
                    }
                    .payment-config-active {
                        border-left: 3px solid #28a745;
                    }
                    .payment-config-inactive {
                        border-left: 3px solid #dc3545;
                        opacity: 0.7;
                    }
                `)
                .appendTo('head');
        }
    }
});
