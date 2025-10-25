#!/usr/bin/env python3
"""
Test Closing Date Notifications Task
"""

import frappe
from frappe.utils import getdate

def execute():
    """Test the closing date notifications functionality"""
    try:
        print("=== Testing Closing Date Notifications ===")
        
        current_date = getdate()
        current_day = current_date.day
        print(f"Current date: {current_date}, Testing for closing day: {current_day}")
        
        # Check if there are any tradelines with closing date matching today
        current_year = current_date.year
        current_month = current_date.month
        
        test_query = """
            SELECT 
                ct.name as client_tradeline_id,
                ct.customer_name,
                ct.tradeline_name,
                tb.bank_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                c.email_id as client_email,
                DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0'))) as calculated_closing_date,
                CASE 
                    WHEN CAST(t.closing_date AS UNSIGNED) > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) THEN 'invalid_date'
                    ELSE 'valid_date'
                END as date_status
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Active'
            AND t.closing_date IS NOT NULL
            AND t.closing_date != ''
            AND CAST(t.closing_date AS UNSIGNED) BETWEEN 1 AND 31
            LIMIT 10
        """
        
        all_tradelines = frappe.db.sql(test_query, (
            current_year, current_month,  # For calculated_closing_date
            current_year, current_month   # For date_status calculation
        ), as_dict=True)
        
        print(f"Found {len(all_tradelines)} active tradelines with closing dates:")
        for tl in all_tradelines:
            print(f"  - {tl.customer_name}: {tl.bank_name} (Closing date: {tl.calculated_closing_date}, Status: {tl.date_status}, Email: {tl.client_email})")
        
        # Check for tradelines closing today
        todays_tradelines = [tl for tl in all_tradelines if str(tl.calculated_closing_date) == str(current_date)]
        
        if todays_tradelines:
            print(f"\n✅ Found {len(todays_tradelines)} tradelines closing today:")
            for tl in todays_tradelines:
                print(f"  - {tl.customer_name}: {tl.bank_name}")
                
            # Test the notification function
            from rockettradeline.tasks import check_and_send_closing_date_notifications
            
            print(f"\n=== Running closing date notifications check ===")
            result = check_and_send_closing_date_notifications()
            
            print(f"Result: {result}")
            
        else:
            print(f"\n⚠️  No tradelines closing today (day {current_day})")
            
            # Show what days have closing tradelines
            closing_days = {}
            for tl in all_tradelines:
                day = tl.closing_day
                if day not in closing_days:
                    closing_days[day] = 0
                closing_days[day] += 1
            
            print("Tradelines by closing day:")
            for day, count in sorted(closing_days.items()):
                print(f"  - Day {day}: {count} tradelines")
                
            # Test with a day that has tradelines
            if closing_days:
                test_day = list(closing_days.keys())[0]
                print(f"\n=== Testing with day {test_day} ===")
                
                # Temporarily modify current date for testing
                original_getdate = frappe.utils.getdate
                
                def mock_getdate():
                    mock_date = current_date.replace(day=test_day)
                    return mock_date
                
                # Apply the mock
                frappe.utils.getdate = mock_getdate
                
                try:
                    from rockettradeline.tasks import check_and_send_closing_date_notifications
                    result = check_and_send_closing_date_notifications()
                    print(f"Test result for day {test_day}: {result}")
                finally:
                    # Restore original function
                    frappe.utils.getdate = original_getdate
        
        return {
            "success": True,
            "current_day": current_day,
            "total_tradelines": len(all_tradelines),
            "todays_tradelines": len(todays_tradelines) if todays_tradelines else 0
        }
        
    except Exception as e:
        error_msg = f"Test failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()