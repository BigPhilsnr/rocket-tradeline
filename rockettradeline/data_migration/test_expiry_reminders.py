#!/usr/bin/env python3
"""
Test Expiry Reminder Notifications
Verify that the expiry reminder system works correctly
"""

import frappe
from frappe.utils import getdate, add_days

def execute():
    """Test the expiry reminder notifications functionality"""
    try:
        print("=== Testing Expiry Reminder Notifications ===")
        
        current_date = getdate()
        expiry_threshold_date = add_days(current_date, 7)
        
        print(f"Current date: {current_date}")
        print(f"Checking for tradelines expiring between {current_date} and {expiry_threshold_date}")
        
        # Check for tradelines expiring within 7 days
        test_query = """
            SELECT 
                ct.name as client_tradeline_id,
                ct.customer_name,
                ct.tradeline_name,
                ct.expiry_date,
                tb.bank_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                c.email_id as client_email,
                DATEDIFF(ct.expiry_date, %s) as days_until_expiry
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Active'
            AND ct.expiry_date IS NOT NULL
            LIMIT 10
        """
        
        all_tradelines = frappe.db.sql(test_query, (current_date,), as_dict=True)
        
        print(f"Found {len(all_tradelines)} active tradelines with expiry dates:")
        for tl in all_tradelines:
            expiry_status = "EXPIRING SOON" if tl.days_until_expiry <= 7 and tl.days_until_expiry > 0 else "NOT YET"
            print(f"  - {tl.customer_name}: {tl.bank_name} | Expires: {tl.expiry_date} | Days: {tl.days_until_expiry} | Status: {expiry_status} | Email: {tl.client_email}")
        
        # Check for tradelines expiring within 7 days
        expiring_tradelines = [tl for tl in all_tradelines if tl.days_until_expiry <= 7 and tl.days_until_expiry > 0]
        
        if expiring_tradelines:
            print(f"\n✅ Found {len(expiring_tradelines)} tradelines expiring within 7 days:")
            for tl in expiring_tradelines:
                print(f"  - {tl.customer_name}: {tl.bank_name} (expires in {tl.days_until_expiry} days)")
                
            # Test the notification function
            from rockettradeline.tasks import check_and_send_expiry_reminders
            
            print(f"\n=== Running expiry reminder notifications check ===")
            result = check_and_send_expiry_reminders()
            
            print(f"Result: {result}")
            
        else:
            print(f"\n⚠️  No tradelines expiring within 7 days")
            
            # Show distribution of expiry dates
            expiry_distribution = {}
            for tl in all_tradelines:
                days = tl.days_until_expiry
                if days not in expiry_distribution:
                    expiry_distribution[days] = 0
                expiry_distribution[days] += 1
            
            print("Tradelines by days until expiry:")
            for days, count in sorted(expiry_distribution.items()):
                status = "✅ WILL TRIGGER" if 0 < days <= 7 else "⏳ Future" if days > 7 else "❌ Past Due"
                print(f"  - {days:3d} days: {count:2d} tradelines ({status})")
        
        # Test the admin functions
        print(f"\n=== Testing Admin Functions ===")
        
        try:
            from rockettradeline.tasks import get_expiring_soon_tradelines
            admin_result = get_expiring_soon_tradelines(7)
            print(f"Admin function result: Found {admin_result['total']} expiring tradelines")
        except Exception as e:
            print(f"Admin function test failed: {str(e)}")
        
        return {
            "success": True,
            "total_tradelines": len(all_tradelines),
            "expiring_tradelines": len(expiring_tradelines),
            "test_date": str(current_date),
            "threshold_date": str(expiry_threshold_date)
        }
        
    except Exception as e:
        error_msg = f"Test failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()