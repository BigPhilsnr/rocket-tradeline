import frappe
from datetime import timedelta
from frappe.utils import getdate, add_days

def execute():
    """
    Revert expiry dates for external customers back to the old calculation (61 days from completion_date)
    Only keep the fix for internal/test accounts
    """
    
    # List of all Client Tradelines that were fixed
    fixed_ct_ids = [
        "CT-00000051", "CT-00000095", "CT-00000096", "CT-00000084", "CT-00000086",
        "CT-00000088", "CT-00000092", "CT-00000077", "CT-00000079", "CT-00000075",
        "CT-00000073", "CT-00000054", "CT-00000059", "CT-00000062", "CT-00000064",
        "CT-00000066", "CT-00000068", "CT-00000071", "CT-00000057",
        "Philip Ademba-00000000024", "Ijeoma O-00000000010"
    ]
    
    # Internal/test email domains and patterns
    internal_patterns = ['rocket', 'test', 'demo', 'admin']
    internal_emails = [
        'admin@rockettradeline.com',
        'test@rockettradeline.com',
    ]
    
    print(f"\n{'='*80}")
    print(f"Reverting expiry dates for external customers")
    print(f"{'='*80}\n")
    
    reverted_count = 0
    kept_count = 0
    error_count = 0
    
    for ct_id in fixed_ct_ids:
        try:
            # Get Client Tradeline document
            ct_doc = frappe.get_doc("Client Tradelines", ct_id)
            
            # Get customer info
            customer_id = ct_doc.customer
            customer_doc = frappe.get_doc("Customer", customer_id) if customer_id else None
            
            customer_email = customer_doc.email_id if customer_doc else "No email"
            customer_name = customer_doc.customer_name if customer_doc else customer_id or "Unknown"
            
            # Check if it's internal/test
            is_internal = False
            
            if customer_email in internal_emails:
                is_internal = True
            
            email_lower = customer_email.lower()
            for pattern in internal_patterns:
                if pattern in email_lower:
                    is_internal = True
                    break
            
            if is_internal:
                # Keep the new calculation for internal accounts
                print(f"🔧 KEEPING FIX (Internal): {ct_id}")
                print(f"   Customer: {customer_name}")
                print(f"   Email: {customer_email}")
                print(f"   Expiry: {ct_doc.expiry_date} (using closing date calculation)")
                print()
                kept_count += 1
            else:
                # Revert to old calculation for external customers
                completion_date = getdate(ct_doc.completion_date)
                old_expiry_date = add_days(completion_date, 61)
                current_expiry_date = ct_doc.expiry_date
                
                print(f"↩️  REVERTING (External): {ct_id}")
                print(f"   Customer: {customer_name}")
                print(f"   Email: {customer_email}")
                print(f"   Completion: {completion_date}")
                print(f"   Current Expiry (new): {current_expiry_date}")
                print(f"   Reverting to (old): {old_expiry_date}")
                print(f"   Days difference: {(current_expiry_date - old_expiry_date).days}")
                
                # Revert to old expiry date
                ct_doc.expiry_date = old_expiry_date
                ct_doc.save(ignore_permissions=True)
                
                reverted_count += 1
                print(f"   ✓ Reverted!\n")
                
        except Exception as e:
            error_count += 1
            print(f"Error processing {ct_id}: {str(e)}\n")
            frappe.log_error(f"Error reverting expiry date for {ct_id}: {str(e)}", "Revert Expiry Dates")
    
    # Commit all changes
    frappe.db.commit()
    
    print(f"{'='*80}")
    print(f"Summary:")
    print(f"  Total processed: {len(fixed_ct_ids)}")
    print(f"  External customers reverted: {reverted_count}")
    print(f"  Internal accounts kept: {kept_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*80}\n")
    
    return {
        "total": len(fixed_ct_ids),
        "reverted": reverted_count,
        "kept": kept_count,
        "errors": error_count
    }
