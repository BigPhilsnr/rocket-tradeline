#!/usr/bin/env python3
"""
Test New Closing Date Logic
Verify that the new date calculation works properly
"""

import frappe
from frappe.utils import getdate

def execute():
    """Test the new closing date logic"""
    try:
        print("=== Testing New Closing Date Logic ===")
        
        current_date = getdate()
        current_year = current_date.year
        current_month = current_date.month
        current_day = current_date.day
        
        print(f"Current date: {current_date} (Year: {current_year}, Month: {current_month}, Day: {current_day})")
        
        # Test the date calculation logic
        test_closing_dates = [1, 15, 28, 30, 31]
        
        print(f"\n=== Testing Date Calculations for Month {current_month}/{current_year} ===")
        
        for closing_day in test_closing_dates:
            # Test if the closing date is valid for current month
            test_query = """
                SELECT 
                    %s as closing_day,
                    DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(%s, 2, '0'))) as calculated_date,
                    DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) as days_in_month,
                    CASE 
                        WHEN %s > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) THEN 'INVALID'
                        ELSE 'VALID'
                    END as date_validity,
                    CASE 
                        WHEN %s > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) THEN 
                            LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))
                        ELSE 
                            DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(%s, 2, '0')))
                    END as effective_date
            """
            
            result = frappe.db.sql(test_query, (
                closing_day,                              # closing_day
                current_year, current_month, closing_day,  # calculated_date
                current_year, current_month,              # days_in_month
                closing_day, current_year, current_month, # date_validity
                closing_day, current_year, current_month, # effective_date CASE condition
                current_year, current_month,              # effective_date LAST_DAY
                current_year, current_month, closing_day  # effective_date DATE
            ), as_dict=True)
            
            if result:
                r = result[0]
                print(f"  Closing Day {closing_day:2d}: {r.calculated_date} | Validity: {r.date_validity:7s} | Effective: {r.effective_date} | Days in month: {r.days_in_month}")
        
        # Test with actual tradelines data
        print(f"\n=== Testing with Actual Tradelines Data ===")
        
        actual_query = """
            SELECT 
                t.closing_date,
                COUNT(*) as count,
                DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0'))) as calculated_date,
                CASE 
                    WHEN CAST(t.closing_date AS UNSIGNED) > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) THEN 'INVALID'
                    ELSE 'VALID'
                END as date_validity
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            WHERE ct.status = 'Active'
            AND t.closing_date IS NOT NULL
            AND t.closing_date != ''
            AND CAST(t.closing_date AS UNSIGNED) BETWEEN 1 AND 31
            GROUP BY t.closing_date
            ORDER BY CAST(t.closing_date AS UNSIGNED)
        """
        
        actual_results = frappe.db.sql(actual_query, (
            current_year, current_month,  # For calculated_date
            current_year, current_month   # For date_validity
        ), as_dict=True)
        
        if actual_results:
            print("Actual tradelines closing dates in system:")
            for r in actual_results:
                print(f"  Day {r.closing_date:2s}: {r.count:2d} tradelines | Calculated: {r.calculated_date} | Validity: {r.date_validity}")
        else:
            print("No active client tradelines found with closing dates")
        
        # Check if any would trigger today
        todays_matches = [r for r in actual_results if str(r.calculated_date) == str(current_date)]
        
        if todays_matches:
            print(f"\n✅ Found {len(todays_matches)} closing date matches for today ({current_date}):")
            for match in todays_matches:
                print(f"  - Closing day {match.closing_date}: {match.count} tradelines")
        else:
            print(f"\n⚠️  No tradelines closing today ({current_date})")
        
        return {
            "success": True,
            "current_date": str(current_date),
            "test_results": len(test_closing_dates),
            "actual_closing_dates": len(actual_results),
            "todays_matches": len(todays_matches)
        }
        
    except Exception as e:
        error_msg = f"Test failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()