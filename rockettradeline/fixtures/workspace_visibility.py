"""
Fixture to hide all standard workspaces except Home and Rocket Tradeline
"""

import frappe

def execute():
	"""Hide all workspaces except Home and Rocket Tradeline"""
	
	# Get all workspaces
	workspaces = frappe.get_all("Workspace", fields=["name", "title", "module"])
	
	# Define workspaces to keep visible
	visible_workspaces = ["Home", "Rocket Tradeline"]
	
	# Hide all other workspaces
	for workspace in workspaces:
		if workspace.get("title") not in visible_workspaces and workspace.get("name") not in visible_workspaces:
			try:
				workspace_doc = frappe.get_doc("Workspace", workspace.name)
				workspace_doc.is_hidden = 1
				workspace_doc.public = 0
				workspace_doc.save(ignore_permissions=True)
				frappe.db.commit()
				print(f"Hidden workspace: {workspace.name}")
			except Exception as e:
				print(f"Error hiding workspace {workspace.name}: {str(e)}")
				continue
	
	# Ensure Rocket Tradeline workspace is visible
	try:
		if frappe.db.exists("Workspace", "Rocket Tradeline"):
			rocket_workspace = frappe.get_doc("Workspace", "Rocket Tradeline")
			rocket_workspace.is_hidden = 0
			rocket_workspace.public = 1
			rocket_workspace.save(ignore_permissions=True)
			frappe.db.commit()
			print("Rocket Tradeline workspace set to visible")
	except Exception as e:
		print(f"Error setting Rocket Tradeline visibility: {str(e)}")
