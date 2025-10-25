import frappe

def execute():
    """
    Check which of the fixed Client Tradelines belong to external (real) customers
    """
    
    # List of Client Tradelines that were fixed
    fixed_ct_ids = [
        "CT-00000051", "CT-00000095", "CT-00000096", "CT-00000084", "CT-00000086",
        "CT-00000088", "CT-00000092", "CT-00000077", "CT-00000079", "CT-00000075",
        "CT-00000073", "CT-00000054", "CT-00000059", "CT-00000062", "CT-00000064",
        "CT-00000066", "CT-00000068", "CT-00000071", "CT-00000057",
        "Philip Ademba-00000000024", "Ijeoma O-00000000010"
    ]
    
    print(f"\n{'='*80}")
    print(f"Checking {len(fixed_ct_ids)} fixed Client Tradelines for external customers")
    print(f"{'='*80}\n")
    
    external_count = 0
    internal_count = 0
    
    # Internal/test email domains and patterns to identify test accounts
    internal_patterns = [
        'rocket', 'test', 'demo', 'admin', 'example.com', 
        'gmail.com', 'yahoo.com'  # Add specific test emails if known
    ]
    
    # Specific internal emails (if any)
    internal_emails = [
        'admin@rockettradeline.com',
        'test@rockettradeline.com',
        # Add any other known internal test emails
    ]
    
    for ct_id in fixed_ct_ids:
        try:
            # Get Client Tradeline document
            ct_doc = frappe.get_doc("Client Tradelines", ct_id)
            
            # Get customer info - use the customer link field
            customer_id = ct_doc.customer
            customer_doc = frappe.get_doc("Customer", customer_id) if customer_id else None
            
            customer_email = customer_doc.email_id if customer_doc else "No email"
            customer_name = customer_doc.customer_name if customer_doc else customer_id or "Unknown"
            
            # Check if it's internal/test
            is_internal = False
            
            # Check against internal emails
            if customer_email in internal_emails:
                is_internal = True
            
            # Check email patterns (case insensitive)
            email_lower = customer_email.lower()
            for pattern in internal_patterns:
                if pattern in email_lower and pattern in ['rocket', 'test', 'demo', 'admin']:
                    is_internal = True
                    break
            
            # Get tradeline info
            tradeline = ct_doc.tradeline
            completion_date = ct_doc.completion_date
            expiry_date = ct_doc.expiry_date
            status = ct_doc.status or "Unknown"
            
            if is_internal:
                internal_count += 1
                marker = "🔧 INTERNAL/TEST"
            else:
                external_count += 1
                marker = "👤 EXTERNAL CUSTOMER"
            
            print(f"{marker}")
            print(f"  Client Tradeline: {ct_id}")
            print(f"  Customer: {customer_name}")
            print(f"  Email: {customer_email}")
            print(f"  Tradeline: {tradeline}")
            print(f"  Status: {status}")
            print(f"  Completion: {completion_date}")
            print(f"  New Expiry: {expiry_date}")
            print()
            
        except Exception as e:
            print(f"Error checking {ct_id}: {str(e)}\n")
    
    print(f"{'='*80}")
    print(f"Summary:")
    print(f"  Total fixed: {len(fixed_ct_ids)}")
    print(f"  External customers: {external_count}")
    print(f"  Internal/test accounts: {internal_count}")
    print(f"{'='*80}\n")
    
    return {
        "total": len(fixed_ct_ids),
        "external": external_count,
        "internal": internal_count
    }
