import frappe
from datetime import date
from frappe.utils import getdate, add_months, add_days, today

def execute():
    """
    Fix expiry dates that were calculated incorrectly (61 days from completion_date)
    Should be: 61 days from next closing date after completion_date
    """
    
    # Get all Client Tradelines with completion_date and expiry_date set
    client_tradelines = frappe.get_all(
        "Client Tradelines",
        filters={
            "completion_date": ["is", "set"],
            "expiry_date": ["is", "set"]
        },
        fields=["name", "tradeline", "completion_date", "expiry_date"]
    )
    
    print(f"\n{'='*80}")
    print(f"Found {len(client_tradelines)} Client Tradelines with completion and expiry dates")
    print(f"{'='*80}\n")
    
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for ct in client_tradelines:
        try:
            # Get the tradeline to access closing_date
            tradeline_doc = frappe.get_doc("Tradeline", ct.tradeline)
            closing_date = tradeline_doc.closing_date or 15
            
            # Get completion date
            completion_date = getdate(ct.completion_date)
            current_day = completion_date.day
            
            # Calculate the correct next closing date
            if current_day < closing_date:
                # Next closing date is this month
                next_closing_date = date(completion_date.year, completion_date.month, closing_date)
            else:
                # Next closing date is next month
                next_month = add_months(completion_date, 1)
                next_month_date = getdate(next_month)
                next_closing_date = date(next_month_date.year, next_month_date.month, closing_date)
            
            # Calculate correct expiry date (61 days after next closing date)
            correct_expiry_date = add_days(next_closing_date, 61)
            
            # Get current expiry date
            current_expiry_date = getdate(ct.expiry_date)
            
            # Calculate what the wrong expiry date would be (61 days from completion)
            wrong_expiry_date = add_days(completion_date, 61)
            
            # Check if current expiry matches the wrong calculation
            if current_expiry_date == wrong_expiry_date and current_expiry_date != correct_expiry_date:
                # This needs fixing
                print(f"Fixing: {ct.name}")
                print(f"  Tradeline: {ct.tradeline} (Closing: {closing_date})")
                print(f"  Completion Date: {completion_date}")
                print(f"  Next Closing Date: {next_closing_date}")
                print(f"  Wrong Expiry (old): {current_expiry_date}")
                print(f"  Correct Expiry (new): {correct_expiry_date}")
                print(f"  Days difference: {(correct_expiry_date - current_expiry_date).days}")
                
                # Update the document
                client_tradeline_doc = frappe.get_doc("Client Tradelines", ct.name)
                client_tradeline_doc.expiry_date = correct_expiry_date
                client_tradeline_doc.save(ignore_permissions=True)
                
                fixed_count += 1
                print(f"  ✓ Fixed!\n")
                
            elif current_expiry_date != correct_expiry_date:
                # Different from both calculations - might need manual review
                print(f"Review needed: {ct.name}")
                print(f"  Tradeline: {ct.tradeline} (Closing: {closing_date})")
                print(f"  Completion Date: {completion_date}")
                print(f"  Current Expiry: {current_expiry_date}")
                print(f"  Expected Expiry: {correct_expiry_date}")
                print(f"  Wrong Expiry: {wrong_expiry_date}")
                print(f"  → Doesn't match either calculation pattern\n")
                skipped_count += 1
            else:
                # Already correct
                skipped_count += 1
                
        except Exception as e:
            error_count += 1
            print(f"Error processing {ct.name}: {str(e)}\n")
            frappe.log_error(f"Error fixing expiry date for {ct.name}: {str(e)}", "Fix Expiry Dates")
    
    # Commit all changes
    frappe.db.commit()
    
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total records: {len(client_tradelines)}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Skipped (already correct or needs review): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*80}\n")
    
    return {
        "total": len(client_tradelines),
        "fixed": fixed_count,
        "skipped": skipped_count,
        "errors": error_count
    }
