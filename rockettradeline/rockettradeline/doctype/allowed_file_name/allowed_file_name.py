# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class AllowedFileName(Document):
    def before_insert(self):
        """Set created date before inserting"""
        self.created_date = now_datetime()
        
    def before_save(self):
        """Set modified date before saving"""
        self.modified_date = now_datetime()
        
    def validate(self):
        """Validate the file name"""
        if not self.file_name:
            frappe.throw("File name is required")
            
        # Check for duplicate active file names
        if self.is_active:
            existing = frappe.get_all("Allowed File Name", 
                filters={
                    "file_name": self.file_name,
                    "is_active": 1,
                    "name": ["!=", self.name]
                },
                limit=1
            )
            
            if existing:
                frappe.throw(f"An active file name '{self.file_name}' already exists")
                
        # Clean file name (remove spaces, convert to lowercase with underscores)
        if self.file_name:
            self.file_name = self.file_name.strip().lower().replace(" ", "_")

    def on_update(self):
        """Clear cache when file names are updated"""
        frappe.clear_cache()
        
    def on_trash(self):
        """Clear cache when file names are deleted"""
        frappe.clear_cache()

@frappe.whitelist()
def get_allowed_file_names():
    """Get all active allowed file names"""
    try:
        file_names = frappe.get_all("Allowed File Name",
            filters={"is_active": 1},
            fields=["file_name", "description", "category"],
            order_by="category asc, file_name asc"
        )
        
        return {
            "success": True,
            "file_names": [item.file_name for item in file_names],
            "detailed_list": file_names
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting allowed file names: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "file_names": []
        }

@frappe.whitelist()
def add_allowed_file_name(file_name, description=None, category="Other"):
    """Add a new allowed file name (Admin only)"""
    try:
        # Check permissions
        if not frappe.has_permission("Allowed File Name", "create"):
            frappe.throw("Permission denied: Cannot create allowed file names")
            
        if not file_name:
            frappe.throw("File name is required")
            
        # Clean the file name
        clean_name = file_name.strip().lower().replace(" ", "_")
        
        # Check if already exists
        existing = frappe.db.exists("Allowed File Name", clean_name)
        if existing:
            frappe.throw(f"File name '{clean_name}' already exists")
            
        # Create new document
        doc = frappe.get_doc({
            "doctype": "Allowed File Name",
            "file_name": clean_name,
            "description": description,
            "category": category,
            "is_active": 1
        })
        
        doc.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"File name '{clean_name}' added successfully",
            "file_name": clean_name
        }
        
    except Exception as e:
        frappe.log_error(f"Error adding allowed file name: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def remove_allowed_file_name(file_name):
    """Remove an allowed file name (Admin only)"""
    try:
        # Check permissions
        if not frappe.has_permission("Allowed File Name", "delete"):
            frappe.throw("Permission denied: Cannot delete allowed file names")
            
        if not file_name:
            frappe.throw("File name is required")
            
        # Check if exists
        if not frappe.db.exists("Allowed File Name", file_name):
            frappe.throw(f"File name '{file_name}' not found")
            
        # Delete the document
        frappe.delete_doc("Allowed File Name", file_name)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"File name '{file_name}' removed successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error removing allowed file name: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def toggle_file_name_status(file_name, is_active):
    """Toggle active status of a file name (Admin only)"""
    try:
        # Check permissions
        if not frappe.has_permission("Allowed File Name", "write"):
            frappe.throw("Permission denied: Cannot update allowed file names")
            
        if not file_name:
            frappe.throw("File name is required")
            
        # Get the document
        doc = frappe.get_doc("Allowed File Name", file_name)
        doc.is_active = int(is_active)
        doc.save()
        frappe.db.commit()
        
        status = "activated" if is_active else "deactivated"
        return {
            "success": True,
            "message": f"File name '{file_name}' {status} successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error toggling file name status: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }