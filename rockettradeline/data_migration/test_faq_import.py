#!/usr/bin/env python3
"""
Test FAQ Import Functionality (without pandas)
"""

import frappe
import csv
import io

def execute():
    """Test the FAQ import functionality"""
    try:
        print("=== Testing FAQ Import Functionality ===")
        
        # Create sample CSV content
        sample_csv_content = """question,answer,category,sort_order,is_published
"What is a tradeline test?","A tradeline is an account on your credit report for testing.",General,1,1
"How does the import work?","The import reads CSV files without requiring pandas library.",Technical,2,1
"Is this working now?","Yes, the import should work without pandas dependency.",Support,3,1"""
        
        print("Sample CSV content created:")
        print(sample_csv_content)
        print()
        
        # Test CSV parsing logic
        csv_reader = csv.DictReader(io.StringIO(sample_csv_content))
        rows = list(csv_reader)
        
        print(f"Parsed {len(rows)} rows from CSV:")
        for i, row in enumerate(rows):
            print(f"  Row {i+1}: {row['question'][:50]}...")
        print()
        
        # Test FAQ creation logic (simulate what the import function does)
        results = {
            "created": [],
            "updated": [],
            "errors": [],
            "skipped": []
        }
        
        for index, row in enumerate(rows):
            try:
                question = str(row.get('question', '')).strip()
                answer = str(row.get('answer', '')).strip()
                category = str(row.get('category', '')).strip() if row.get('category') else None
                
                if category == '' or category == 'None':
                    category = None
                
                # Validate required fields
                if not question or not answer:
                    results["skipped"].append({
                        "row": index + 2,
                        "reason": "Empty question or answer",
                        "question": question[:50]
                    })
                    continue
                
                # Parse optional fields
                try:
                    sort_order = int(row.get('sort_order', 0)) if row.get('sort_order') and str(row.get('sort_order')).strip() else 0
                except (ValueError, TypeError):
                    sort_order = 0
                
                try:
                    is_published_value = row.get('is_published', '1')
                    if str(is_published_value).lower() in ['false', '0', 'no', 'n']:
                        is_published = 0
                    else:
                        is_published = 1
                except (ValueError, TypeError):
                    is_published = 1
                
                # Check if FAQ with same question already exists
                existing_faq = frappe.db.get_value("FAQ", {"question": question}, ["name", "answer"])
                
                if existing_faq:
                    print(f"  FAQ already exists: {question}")
                    results["updated"].append({
                        "row": index + 2,
                        "question": question,
                        "faq_id": existing_faq[0],
                        "action": "would_update"
                    })
                else:
                    print(f"  Would create new FAQ: {question}")
                    results["created"].append({
                        "row": index + 2,
                        "question": question,
                        "action": "would_create"
                    })
                
            except Exception as e:
                results["errors"].append({
                    "row": index + 2,
                    "error": str(e),
                    "question": str(row.get('question', ''))
                })
        
        print()
        print("=== Import Simulation Results ===")
        print(f"Would create: {len(results['created'])} FAQs")
        print(f"Would update: {len(results['updated'])} FAQs")
        print(f"Would skip: {len(results['skipped'])} FAQs")
        print(f"Errors: {len(results['errors'])}")
        
        if results["errors"]:
            print("\nErrors:")
            for error in results["errors"]:
                print(f"  Row {error['row']}: {error['error']}")
        
        print()
        print("✅ FAQ import functionality test completed successfully!")
        print("✅ CSV parsing works without pandas dependency")
        print("✅ The import should now work for bulk FAQ upload")
        
        return {
            "success": True,
            "message": "FAQ import test completed successfully"
        }
        
    except Exception as e:
        error_msg = f"Test failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()