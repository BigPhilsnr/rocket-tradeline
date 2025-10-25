frappe.ui.form.on("Tradeline Import Item", {
    customer_exists: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Clear existing customer selection when checkbox is unchecked
        if (!row.customer_exists) {
            frappe.model.set_value(cdt, cdn, "existing_customer", "");
            frappe.model.set_value(cdt, cdn, "customer_email", "");
            frappe.model.set_value(cdt, cdn, "customer_name", "");
        }
    },

    existing_customer: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Only fetch customer details if customer is selected
        if (row.existing_customer && row.customer_exists) {
            frappe.call({
                method: "rockettradeline.rockettradeline.doctype.tradeline_import_item.tradeline_import_item.get_customer_details",
                args: {
                    customer_name: row.existing_customer
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        let customer = r.message.customer;

                        // Auto-populate customer details
                        frappe.model.set_value(cdt, cdn, "customer_email", customer.email_id || "");
                        frappe.model.set_value(cdt, cdn, "customer_name", customer.customer_name || "");
                        frappe.model.set_value(cdt, cdn, "customer_phone", customer.mobile_no || "");

                        // Show success message
                        frappe.show_alert({
                            message: __("Customer details auto-populated"),
                            indicator: "green"
                        });
                    } else {
                        frappe.show_alert({
                            message: r.message ? r.message.message : __("Failed to fetch customer details"),
                            indicator: "red"
                        });
                    }
                },
                error: function(r) {
                    frappe.show_alert({
                        message: __("Failed to fetch customer details"),
                        indicator: "red"
                    });
                }
            });
        }
    },

    // Calculate total amount when quantity, unit_price, discount_type, or discount_value changes
    quantity: function(frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    },

    unit_price: function(frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    },

    discount_type: function(frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    },

    discount_value: function(frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    }
});

// Function to calculate total amount
function calculate_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let quantity = row.quantity || 0;
    let unit_price = row.unit_price || 0;
    let discount_type = row.discount_type;
    let discount_value = row.discount_value || 0;
    
    // Calculate subtotal
    let subtotal = quantity * unit_price;
    
    // Calculate discount amount
    let discount_amount = 0;
    if (discount_type === "Percentage" && discount_value > 0) {
        discount_amount = subtotal * (discount_value / 100);
    } else if (discount_type === "Amount" && discount_value > 0) {
        discount_amount = discount_value;
    }
    
    // Calculate total
    let total = subtotal - discount_amount;
    
    // Update the total_amount field
    frappe.model.set_value(cdt, cdn, "total_amount", total);
}