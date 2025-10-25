import frappe
from frappe.utils import getdate
from datetime import date

def execute():
    """
    Restore correct expiry dates for external customers (imported from external system)
    These dates were correct originally and should not have been reverted
    """
    
    # Mapping of Client Tradelines to their correct imported expiry dates
    correct_expiry_dates = {
        "CT-00000051": "2026-01-01",
        "CT-00000095": "2025-12-24",
        "CT-00000096": "2025-12-24",
        "CT-00000084": "2025-12-25",
        "CT-00000086": "2025-12-25",
        "CT-00000088": "2025-12-25",
        "CT-00000092": "2025-12-27",
        "CT-00000077": "2025-12-19",
        "CT-00000079": "2025-12-19",
        "CT-00000075": "2025-12-19",
        "CT-00000073": "2025-12-24",
        "CT-00000054": "2026-01-14",
        "CT-00000059": "2026-01-14",
        "CT-00000062": "2026-01-14",
        "CT-00000064": "2026-01-14",
        "CT-00000066": "2026-01-14",
        "CT-00000068": "2026-01-14",
        "CT-00000071": "2025-12-19",
        "CT-00000057": "2026-01-14",
        "Philip Ademba-00000000024": "2025-12-27",
        "Ijeoma O-00000000010": "2026-01-01",
    }
    
    print(f"\n{'='*80}")
    print(f"Restoring correct imported expiry dates for external customers")
    print(f"{'='*80}\n")
    
    restored_count = 0
    error_count = 0
    
    for ct_id, correct_expiry in correct_expiry_dates.items():
        try:
            # Get Client Tradeline document
            ct_doc = frappe.get_doc("Client Tradelines", ct_id)
            
            # Get customer info
            customer_id = ct_doc.customer
            customer_doc = frappe.get_doc("Customer", customer_id) if customer_id else None
            customer_name = customer_doc.customer_name if customer_doc else customer_id or "Unknown"
            customer_email = customer_doc.email_id if customer_doc else "No email"
            
            current_expiry = ct_doc.expiry_date
            correct_expiry_date = getdate(correct_expiry)
            completion_date = ct_doc.completion_date
            
            if current_expiry != correct_expiry_date:
                print(f"✓ RESTORING: {ct_id}")
                print(f"  Customer: {customer_name}")
                print(f"  Email: {customer_email}")
                print(f"  Completion: {completion_date}")
                print(f"  Current (wrong): {current_expiry}")
                print(f"  Restoring to (correct imported): {correct_expiry_date}")
                print(f"  Days difference: {(correct_expiry_date - current_expiry).days}")
                
                # Restore correct expiry date
                ct_doc.expiry_date = correct_expiry_date
                ct_doc.save(ignore_permissions=True)
                
                restored_count += 1
                print(f"  ✓ Restored!\n")
            else:
                print(f"✓ ALREADY CORRECT: {ct_id}")
                print(f"  Customer: {customer_name}")
                print(f"  Expiry: {current_expiry}\n")
                
        except Exception as e:
            error_count += 1
            print(f"Error processing {ct_id}: {str(e)}\n")
            frappe.log_error(f"Error restoring expiry date for {ct_id}: {str(e)}", "Restore Expiry Dates")
    
    # Commit all changes
    frappe.db.commit()
    
    print(f"{'='*80}")
    print(f"Summary:")
    print(f"  Total processed: {len(correct_expiry_dates)}")
    print(f"  Restored: {restored_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*80}\n")
    print("Note: These expiry dates were imported from an external system and")
    print("represent the correct billing cycle calculations.")
    print(f"{'='*80}\n")
    
    return {
        "total": len(correct_expiry_dates),
        "restored": restored_count,
        "errors": error_count
    }
