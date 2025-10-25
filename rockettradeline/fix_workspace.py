#!/usr/bin/env python3
"""
Fix RocketTradeline workspace with proper shortcuts
"""

import frappe
import json


def fix_workspace():
	"""Fix RocketTradeline workspace"""
	
	frappe.init(site="rockettradeline.com")
	frappe.connect()
	frappe.flags.in_install = True
	
	def generate_id():
		import random, string
		return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
	
	workspace_name = "RocketTradeline"
	ws = frappe.get_doc("Workspace", workspace_name)
	
	# Clear shortcuts
	ws.shortcuts = []
	
	# Define sections and doctypes
	sections = [
		("Tradeline Management", [
			"Client Tradelines", "Tradeline", "Tradeline Bank", "Tradeline Cart"
		]),
		("Customer & Payments", [
			"Customer", "Payment Request", "Payment Configuration", "Mode of Payment"
		]),
		("Email & Notifications", [
			"Email Template Custom", "Email Account", "Email Group", "Notification Log"
		]),
		("Content & Settings", [
			"Site Content", "Page Content", "FAQ", "Testimonial", "User", "Address", "Contact"
		])
	]
	
	# Add shortcuts
	print("=== Adding Shortcuts ===")
	for section_name, doctypes in sections:
		for dt in doctypes:
			if frappe.db.exists("DocType", dt):
				ws.append("shortcuts", {
					"label": dt,
					"type": "DocType",
					"link_to": dt,
					"doc_view": "List",
					"format": "{} List",
					"icon": "list",
					"color": "grey"
				})
				print(f"  {dt}")
	
	print(f"\nTotal shortcuts added: {len(ws.shortcuts)}")
	
	# Build content
	print("\n=== Building Content ===")
	content = []
	
	for section_name, doctypes in sections:
		# Add header
		content.append({
			"id": generate_id(),
			"type": "header",
			"data": {
				"text": f"<span class=\"h4\"><b>{section_name}</b></span>",
				"col": 12
			}
		})
		print(f"\n{section_name}:")
		
		# Add shortcuts
		for dt in doctypes:
			if frappe.db.exists("DocType", dt):
				content.append({
					"id": generate_id(),
					"type": "shortcut",
					"data": {
						"shortcut_name": dt,
						"col": 3
					}
				})
				print(f"  {dt}")
	
	print(f"\nTotal content items: {len(content)}")
	
	# Save
	ws.content = json.dumps(content)
	ws.flags.ignore_version = True
	ws.flags.ignore_permissions = True
	ws.save()
	frappe.db.commit()
	
	print(f"\n✅ Workspace updated successfully!")
	print(f"   - {len(ws.shortcuts)} shortcuts")
	print(f"   - {len(content)} content items")
	
	frappe.destroy()
	
	return {"success": True, "shortcuts": len(ws.shortcuts), "content_items": len(content)}


if __name__ == "__main__":
	result = fix_workspace()
	print(f"\n{json.dumps(result, indent=2)}")
