#!/usr/bin/env python3
"""
Final Verification of Allowed File Name Records
"""

import frappe

def execute():
    """Verify and display all Allowed File Name records"""
    try:
        print("=== Final Verification of Allowed File Name Records ===")
        
        # Get all records with proper ordering
        records = frappe.get_all("Allowed File Name",
            fields=["name", "file_name", "description", "category", "is_active", "creation"],
            order_by="category asc, file_name asc"
        )
        
        print(f"\n✅ Total Records: {len(records)}")
        
        # Group by category
        categories = {}
        for record in records:
            category = record.category or "Uncategorized"
            if category not in categories:
                categories[category] = []
            categories[category].append(record)
        
        print(f"\n=== Records by Category ===")
        for category, cat_records in categories.items():
            print(f"\n📁 {category} ({len(cat_records)} records):")
            for record in cat_records:
                status = "✅ Active" if record.is_active else "❌ Inactive"
                print(f"   • {record.file_name} - {status}")
                if record.description:
                    print(f"     Description: {record.description}")
        
        # Show new records that weren't in the original patch
        original_patch_records = [
            'dl_front', 'dl_back', 'proof_of_address', 'client_signature', 
            'proof_of_enrollment', 'proof_of_refund', 'credit_report', 
            'authorized_user_guide', 'privacy_policy', 'terms_conditions', 
            'refund_policy', 'authorized_user_agreement'
        ]
        
        new_records = [r for r in records if r.file_name not in original_patch_records]
        
        if new_records:
            print(f"\n🆕 Additional Records from Remote Database ({len(new_records)}):")
            for record in new_records:
                status = "✅ Active" if record.is_active else "❌ Inactive"
                print(f"   • {record.file_name} ({record.category}) - {status}")
        
        return {
            "success": True,
            "total_records": len(records),
            "categories": {cat: len(recs) for cat, recs in categories.items()},
            "new_records": len(new_records),
            "all_records": [r.file_name for r in records]
        }
        
    except Exception as e:
        error_msg = f"Verification failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()