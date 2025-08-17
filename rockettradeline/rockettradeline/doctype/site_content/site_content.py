import frappe
from frappe.model.document import Document

class SiteContent(Document):
    def validate(self):
        # Ensure key is unique
        if self.key:
            existing = frappe.get_all("Site Content", 
                filters={"key": self.key, "name": ["!=", self.name]},
                limit=1
            )
            if existing:
                frappe.throw(f"Key '{self.key}' already exists")
    
    def before_save(self):
        # Auto-generate key if not provided
        if not self.key and self.page and self.section:
            self.key = f"{self.page}_{self.section}".replace(" ", "_").lower()
    
    @staticmethod
    def get_content_by_key(key, default_value=None):
        """Get content value by key"""
        content = frappe.get_all("Site Content", 
            filters={"key": key, "is_active": 1},
            fields=["value"],
            limit=1
        )
        return content[0].value if content else default_value
    
    @staticmethod
    def get_content_by_section_page(section, page):
        """Get all content for a specific section and page"""
        content = frappe.get_all("Site Content",
            filters={"section": section, "page": page, "is_active": 1},
            fields=["key", "value", "content_type"],
            order_by="key asc"
        )
        return content
    
    @staticmethod
    def set_content(key, value, section, page, content_type="Text"):
        """Set content value by key, create if not exists"""
        existing = frappe.get_all("Site Content", 
            filters={"key": key},
            limit=1
        )
        
        if existing:
            doc = frappe.get_doc("Site Content", existing[0].name)
            doc.value = value
            doc.section = section
            doc.page = page
            doc.content_type = content_type
            doc.save()
        else:
            doc = frappe.get_doc({
                "doctype": "Site Content",
                "key": key,
                "value": value,
                "section": section,
                "page": page,
                "content_type": content_type,
                "is_active": 1
            })
            doc.insert()
        
        return doc
