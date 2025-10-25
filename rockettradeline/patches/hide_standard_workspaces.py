import frappe

def execute():
	"""Hide all workspaces except Home and Rocket Tradeline"""
	
	# Get all workspaces
	workspaces = frappe.get_all("Workspace", fields=["name", "title", "module", "public", "is_hidden"])
	
	# Define workspaces to keep visible
	visible_workspaces = ["Home", "Rocket Tradeline"]
	
	# List of workspaces to definitely hide
	workspaces_to_hide = [
		"Accounting", "Selling", "Buying", "Stock", "Assets", "Projects",
		"CRM", "Support", "HR", "Payroll", "Quality", "Manufacturing",
		"Website", "Utilities", "Settings", "Integrations", "Automation",
		"Build", "Tools", "Inventory", "Financial Statements", "Expenses",
		"ERPNext Settings", "ERPNext Integrations", "Erpnext Settings", 
		"Erpnext Integrations", "Healthcare", "Education", "Agriculture",
		"Non Profit", "Loan Management", "Maintenance", "Restaurant"
	]
	
	# Hide all other workspaces
	for workspace in workspaces:
		workspace_name = workspace.get("name")
		workspace_title = workspace.get("title")
		
		# Skip if it's a visible workspace
		if workspace_title in visible_workspaces or workspace_name in visible_workspaces:
			continue
		
		# Hide if it's in the list or not in visible list
		if workspace_title in workspaces_to_hide or workspace_name in workspaces_to_hide:
			try:
				frappe.db.set_value("Workspace", workspace_name, {
					"is_hidden": 1,
					"public": 0
				}, update_modified=False)
				print(f"Hidden workspace: {workspace_name}")
			except Exception as e:
				print(f"Error hiding workspace {workspace_name}: {str(e)}")
				continue
	
	# Ensure Rocket Tradeline workspace is visible and public
	try:
		if frappe.db.exists("Workspace", "Rocket Tradeline"):
			frappe.db.set_value("Workspace", "Rocket Tradeline", {
				"is_hidden": 0,
				"public": 1
			}, update_modified=False)
			print("Rocket Tradeline workspace set to visible")
	except Exception as e:
		print(f"Error setting Rocket Tradeline visibility: {str(e)}")
	
	# Ensure Home workspace is visible
	try:
		if frappe.db.exists("Workspace", "Home"):
			frappe.db.set_value("Workspace", "Home", {
				"is_hidden": 0,
				"public": 1
			}, update_modified=False)
			print("Home workspace set to visible")
	except Exception as e:
		print(f"Error setting Home visibility: {str(e)}")
	
	frappe.db.commit()
