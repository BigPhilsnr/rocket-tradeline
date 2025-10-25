# Copyright (c) 2025, RocketTradeLine and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TradelineImportItem(Document):
	"""
	Child table for Tradeline Import items.
	Each item represents a single tradeline purchase to be imported.
	"""
	pass


@frappe.whitelist()
def get_customer_details(customer_name):
	"""
	Get customer details for auto-population in import form.
	Returns only the essential fields needed for the import form.
	"""
	try:
		if not customer_name:
			return {"success": False, "message": "Customer name is required"}

		# Get customer document with only needed fields
		customer = frappe.get_doc("Customer", customer_name)

		return {
			"success": True,
			"customer": {
				"name": customer.name,
				"customer_name": customer.customer_name,
				"email_id": customer.email_id,
				"mobile_no": customer.mobile_no
			}
		}

	except frappe.DoesNotExistError:
		return {"success": False, "message": "Customer not found"}

	except Exception as e:
		frappe.log_error(f"Error fetching customer details: {str(e)}")
		return {"success": False, "message": "Failed to fetch customer details"}
