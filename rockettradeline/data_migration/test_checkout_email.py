#!/usr/bin/env python3
"""
Test Tradeline Cart Checkout Email Functionality
"""

import frappe

def execute():
    """Test the checkout email functionality"""
    try:
        print("=== Testing Tradeline Cart Checkout Email ===")
        
        # Find a customer with an account manager
        customers_with_managers = frappe.get_all("Customer",
            filters={"account_manager": ["!=", ""]},
            fields=["name", "customer_name", "email_id", "account_manager"],
            limit=5
        )
        
        if not customers_with_managers:
            print("❌ No customers with account managers found")
            return {"success": False, "error": "No test customers available"}
        
        print(f"Found {len(customers_with_managers)} customers with account managers:")
        for customer in customers_with_managers:
            print(f"  - {customer.customer_name} ({customer.email_id}) - Manager: {customer.account_manager}")
        
        # Use the first customer for testing
        test_customer = customers_with_managers[0]
        print(f"\nUsing test customer: {test_customer.customer_name}")
        
        # Check if there's an existing cart for this customer
        existing_carts = frappe.get_all("Tradeline Cart",
            filters={"customer": test_customer.name},
            fields=["name", "status"],
            limit=1
        )
        
        if existing_carts:
            # Use existing cart
            cart_name = existing_carts[0].name
            cart_doc = frappe.get_doc("Tradeline Cart", cart_name)
            print(f"Using existing cart: {cart_name} (Status: {cart_doc.status})")
        else:
            # Create a test cart
            cart_doc = frappe.get_doc({
                "doctype": "Tradeline Cart",
                "customer": test_customer.name,
                "user_id": test_customer.email_id,
                "status": "Active"
            })
            cart_doc.insert(ignore_permissions=True)
            print(f"Created test cart: {cart_doc.name}")
        
        # Test the checkout email by changing status to "Checked Out"
        print(f"\nTesting checkout email by updating cart status...")
        original_status = cart_doc.status
        
        cart_doc.status = "Checked Out"
        cart_doc.save(ignore_permissions=True)
        
        print(f"✅ Cart status updated from '{original_status}' to '{cart_doc.status}'")
        print(f"✅ Checkout notification email should be sent to: {test_customer.email_id}")
        
        return {
            "success": True,
            "cart_name": cart_doc.name,
            "customer_email": test_customer.email_id,
            "customer_name": test_customer.customer_name,
            "account_manager": test_customer.account_manager,
            "message": f"Checkout email triggered for cart {cart_doc.name}"
        }
        
    except Exception as e:
        error_msg = f"Test failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()