#!/usr/bin/env python3
"""
Script to create proper workspace links for RocketTradeline workspace
"""

import frappe
import json


def create_workspace_with_links():
	"""Create RocketTradeline workspace with proper link structure"""
	
	frappe.init(site="rockettradeline.com")
	frappe.connect()
	frappe.flags.in_install = True
	
	workspace_name = "RocketTradeline"
	
	# Get or create workspace
	if frappe.db.exists("Workspace", workspace_name):
		ws = frappe.get_doc("Workspace", workspace_name)
		print(f"Found existing workspace: {workspace_name}")
	else:
		ws = frappe.new_doc("Workspace")
		ws.label = workspace_name
		ws.title = workspace_name
		print(f"Creating new workspace: {workspace_name}")
	
	ws.module = "rockettradeline"
	ws.icon = "list"
	ws.indicator_color = "orange"
	ws.public = 1
	ws.is_hidden = 0
	
	# Clear existing links
	ws.links = []
	
	# Add Card Break
	ws.append("links", {
		"type": "Card Break",
		"label": "Tradeline Management"
	})
	
	# Tradeline doctypes
	tradeline_docs = [
		("Client Tradelines", "Manage client tradeline purchases"),
		("Tradeline", "Tradeline products"),
		("Tradeline Bank", "Bank information"),
		("Tradeline Cart", "Shopping cart"),
	]
	
	for doctype, desc in tradeline_docs:
		if frappe.db.exists("DocType", doctype):
			ws.append("links", {
				"type": "Link",
				"link_type": "DocType",
				"link_to": doctype,
				"label": doctype,
				"description": desc,
				"onboard": 0
			})
	
	# Add another section
	ws.append("links", {
		"type": "Card Break",
		"label": "Customer & Payments"
	})
	
	customer_docs = [
		("Customer", "Customer management"),
		("Payment Request", "Payment requests"),
		("Payment Configuration", "Payment settings"),
		("Mode of Payment", "Payment methods"),
	]
	
	for doctype, desc in customer_docs:
		if frappe.db.exists("DocType", doctype):
			ws.append("links", {
				"type": "Link",
				"link_type": "DocType",
				"link_to": doctype,
				"label": doctype,
				"description": desc,
				"onboard": 0
			})
	
	# Add another section
	ws.append("links", {
		"type": "Card Break",
		"label": "Email & Notifications"
	})
	
	email_docs = [
		("Email Template Custom", "Custom email templates"),
		("Email Account", "Email accounts"),
		("Email Group", "Email groups"),
		("Notification Log", "Notification history"),
	]
	
	for doctype, desc in email_docs:
		if frappe.db.exists("DocType", doctype):
			ws.append("links", {
				"type": "Link",
				"link_type": "DocType",
				"link_to": doctype,
				"label": doctype,
				"description": desc,
				"onboard": 0
			})
	
	# Add another section
	ws.append("links", {
		"type": "Card Break",
		"label": "Content & Settings"
	})
	
	other_docs = [
		("Site Content", "Website content"),
		("Page Content", "Page blocks"),
		("FAQ", "FAQs"),
		("Testimonial", "Testimonials"),
		("User", "User management"),
		("Address", "Addresses"),
		("Contact", "Contacts"),
	]
	
	for doctype, desc in other_docs:
		if frappe.db.exists("DocType", doctype):
			ws.append("links", {
				"type": "Link",
				"link_type": "DocType",
				"link_to": doctype,
				"label": doctype,
				"description": desc,
				"onboard": 0
			})
	
	# Build content from shortcuts
	def generate_id():
		import random, string
		return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
	
	content = []
	
	for section, doctypes in all_doctypes:
		# Add section header
		content.append({
			"id": generate_id(),
			"type": "header",
			"data": {
				"text": f"<span class=\"h4\"><b>{section}</b></span>",
				"col": 12
			}
		})
		
		# Add shortcuts for this section
		for doctype in doctypes:
			if frappe.db.exists("DocType", doctype):
				content.append({
					"id": generate_id(),
					"type": "shortcut",
					"data": {
						"shortcut_name": doctype,
						"col": 3
					}
				})
				print(f"Added to content: {doctype}")
	
	ws.content = json.dumps(content)
	
	# Save
	ws.flags.ignore_version = True
	ws.flags.ignore_permissions = True
	ws.save()
	frappe.db.commit()
	
	print(f"\n✅ Successfully updated workspace: {workspace_name}")
	print(f"Total links: {len(ws.links)}")
	print(f"Content items: {len(content)}")
	print(f"\nSections:")
	section_count = len([l for l in ws.links if l.type == "Card Break"])
	link_count = len([l for l in ws.links if l.type == "Link"])
	print(f"- {section_count} sections")
	print(f"- {link_count} doctype links")
	
	frappe.destroy()
	
	return {"success": True, "workspace": workspace_name, "links": len(ws.links)}


if __name__ == "__main__":
	result = create_workspace_with_links()
	print(f"\n{json.dumps(result, indent=2)}")
