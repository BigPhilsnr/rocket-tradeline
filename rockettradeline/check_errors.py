import frappe

def check_recent_errors():
    """Check recent error logs for email issues"""
    try:
        print("=== Checking Recent Error Logs ===")
        
        # Get recent Error Log entries
        recent_errors = frappe.get_all(
            "Error Log",
            fields=["name", "creation", "error"],
            filters=[["creation", ">=", "2025-08-26"]],
            order_by="creation desc",
            limit=10
        )
        
        print(f"Found {len(recent_errors)} recent error logs:")
        
        for i, error in enumerate(recent_errors):
            error_doc = frappe.get_doc("Error Log", error.name)
            if "Email" in error_doc.error:
                print(f"\n--- Error {i+1}: {error.name} ---")
                print(f"Created: {error.creation}")
                print(f"Error Details:")
                print(error_doc.error[:1000])  # First 1000 characters
                print("---")
                
        return True
        
    except Exception as e:
        print(f"Error checking logs: {str(e)}")
        return False
