// Copyright (c) 2025, RocketTradeline and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tradeline Cart', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.status === 'Active' && !frm.is_new()) {
			frm.add_custom_button(__('Add Item'), function() {
				add_cart_item(frm);
			});
			
			frm.add_custom_button(__('Clear Cart'), function() {
				clear_cart(frm);
			});
			
			frm.add_custom_button(__('Checkout'), function() {
				checkout_cart(frm);
			}).addClass('btn-primary');
		}
		
		if (frm.doc.status === 'Checked Out') {
			frm.add_custom_button(__('View Sales Order'), function() {
				// Logic to view related sales order
				frappe.msgprint('Sales Order functionality to be implemented');
			});
		}
		
		// Show cart summary
		show_cart_summary(frm);
	},
	
	payment_mode: function(frm) {
		if (frm.doc.payment_mode) {
			frm.set_df_property('payment_status', 'reqd', 1);
		}
	},
	
	discount_amount: function(frm) {
		calculate_totals(frm);
	},
	
	tax_amount: function(frm) {
		calculate_totals(frm);
	}
});

frappe.ui.form.on('Tradeline Cart Item', {
	quantity: function(frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
		calculate_totals(frm);
	},
	
	rate: function(frm, cdt, cdn) {
		calculate_item_total(frm, cdt, cdn);
		calculate_totals(frm);
	},
	
	tradeline: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.tradeline) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Tradeline',
					fieldname: ['price', 'bank', 'max_spots'],
					filters: { name: row.tradeline }
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, 'rate', r.message.price);
						frappe.model.set_value(cdt, cdn, 'tradeline_name', r.message.bank);
						
						// Validate quantity against max_spots
						if (row.quantity > r.message.max_spots) {
							frappe.model.set_value(cdt, cdn, 'quantity', r.message.max_spots);
							frappe.msgprint(`Quantity adjusted to maximum available spots: ${r.message.max_spots}`);
						}
						
						calculate_item_total(frm, cdt, cdn);
						calculate_totals(frm);
					}
				}
			});
		}
	}
});

function calculate_item_total(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.quantity && row.rate) {
		row.amount = row.quantity * row.rate;
		frm.refresh_field('items');
	}
}

function calculate_totals(frm) {
	let subtotal = 0;
	
	frm.doc.items.forEach(function(item) {
		if (item.amount) {
			subtotal += item.amount;
		}
	});
	
	frm.set_value('subtotal', subtotal);
	
	let discount = frm.doc.discount_amount || 0;
	let tax = frm.doc.tax_amount || 0;
	let total = subtotal - discount + tax;
	
	frm.set_value('total_amount', total);
}

function add_cart_item(frm) {
	let d = new frappe.ui.Dialog({
		title: 'Add Tradeline to Cart',
		fields: [
			{
				label: 'Tradeline',
				fieldname: 'tradeline',
				fieldtype: 'Link',
				options: 'Tradeline',
				filters: { status: 'Active' },
				reqd: 1
			},
			{
				label: 'Quantity',
				fieldname: 'quantity',
				fieldtype: 'Int',
				default: 1,
				reqd: 1
			}
		],
		primary_action_label: 'Add to Cart',
		primary_action: function(values) {
			frappe.call({
				method: 'rockettradeline.doctype.tradeline_cart.tradeline_cart.add_item_to_cart',
				args: {
					cart_id: frm.doc.name,
					tradeline_id: values.tradeline,
					quantity: values.quantity
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frm.reload_doc();
						frappe.msgprint('Item added to cart successfully');
					}
				}
			});
			d.hide();
		}
	});
	d.show();
}

function clear_cart(frm) {
	frappe.confirm(
		'Are you sure you want to clear all items from the cart?',
		function() {
			frappe.call({
				method: 'rockettradeline.doctype.tradeline_cart.tradeline_cart.clear_cart',
				args: { cart_id: frm.doc.name },
				callback: function(r) {
					if (r.message && r.message.success) {
						frm.reload_doc();
						frappe.msgprint('Cart cleared successfully');
					}
				}
			});
		}
	);
}

function checkout_cart(frm) {
	if (!frm.doc.payment_mode) {
		frappe.msgprint('Please select a payment mode before checkout');
		return;
	}
	
	frappe.confirm(
		'Proceed with checkout? This will create a sales order.',
		function() {
			frappe.call({
				method: 'rockettradeline.doctype.tradeline_cart.tradeline_cart.checkout_cart',
				args: { cart_id: frm.doc.name },
				callback: function(r) {
					if (r.message && r.message.success) {
						frm.reload_doc();
						frappe.msgprint('Checkout completed successfully');
					}
				}
			});
		}
	);
}

function show_cart_summary(frm) {
	if (!frm.is_new() && frm.doc.items && frm.doc.items.length > 0) {
		let html = `
			<div class="cart-summary" style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
				<h5>Cart Summary</h5>
				<div class="row">
					<div class="col-md-6">
						<strong>Items in Cart:</strong> ${frm.doc.items.length}<br>
						<strong>Status:</strong> <span class="indicator ${get_status_color(frm.doc.status)}">${frm.doc.status}</span><br>
						<strong>Expires:</strong> ${frm.doc.cart_expiry ? frappe.datetime.str_to_user(frm.doc.cart_expiry) : 'Not set'}
					</div>
					<div class="col-md-6 text-right">
						<strong>Subtotal:</strong> ${format_currency(frm.doc.subtotal)}<br>
						<strong>Discount:</strong> ${format_currency(frm.doc.discount_amount || 0)}<br>
						<strong>Tax:</strong> ${format_currency(frm.doc.tax_amount || 0)}<br>
						<h5><strong>Total: ${format_currency(frm.doc.total_amount)}</strong></h5>
					</div>
				</div>
			</div>
		`;
		
		frm.dashboard.add_section(html);
	}
}

function get_status_color(status) {
	const colors = {
		'Active': 'green',
		'Abandoned': 'orange',
		'Expired': 'red',
		'Checked Out': 'blue',
		'Processing': 'yellow',
		'Completed': 'green'
	};
	return colors[status] || 'grey';
}

function format_currency(amount) {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD'
	}).format(amount || 0);
}
