// Copyright (c) 2025, philmaxsnr@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Client Tradelines', {
	refresh: function(frm) {
		// Add custom buttons or actions here if needed
	},
	
	quantity: function(frm) {
		calculate_amounts(frm);
	},
	
	unit_price: function(frm) {
		calculate_amounts(frm);
	},
	
	discount_type: function(frm) {
		if (!frm.doc.discount_type) {
			frm.set_value('discount_value', 0);
			frm.set_value('discount_amount', 0);
		}
		calculate_amounts(frm);
	},
	
	discount_value: function(frm) {
		calculate_amounts(frm);
	}
});

function calculate_amounts(frm) {
	if (!frm.doc.quantity || !frm.doc.unit_price) {
		return;
	}
	
	// Calculate subtotal
	let subtotal = flt(frm.doc.quantity) * flt(frm.doc.unit_price);
	frm.set_value('subtotal', subtotal);
	
	// Calculate discount amount
	let discount_amount = 0;
	if (frm.doc.discount_type && frm.doc.discount_value) {
		if (frm.doc.discount_type === 'Percentage') {
			if (flt(frm.doc.discount_value) > 100) {
				frappe.msgprint(__('Percentage discount cannot exceed 100%'));
				frm.set_value('discount_value', 0);
				return;
			}
			discount_amount = (subtotal * flt(frm.doc.discount_value)) / 100;
		} else if (frm.doc.discount_type === 'Amount') {
			if (flt(frm.doc.discount_value) > subtotal) {
				frappe.msgprint(__('Discount amount cannot exceed subtotal of {0}', [subtotal.toFixed(2)]));
				frm.set_value('discount_value', 0);
				return;
			}
			discount_amount = flt(frm.doc.discount_value);
		}
	}
	
	frm.set_value('discount_amount', discount_amount);
	
	// Calculate total amount
	let total_amount = subtotal - discount_amount;
	if (total_amount < 0) {
		total_amount = 0;
	}
	frm.set_value('total_amount', total_amount);
}
