import frappe
import unittest

class TestSiteContent(unittest.TestCase):
    def test_create_site_content(self):
        # Test creating site content
        content = frappe.get_doc({
            "doctype": "Site Content",
            "key": "test_key",
            "value": "test_value",
            "section": "test_section",
            "page": "test_page",
            "content_type": "Text"
        })
        content.insert()
        
        # Test retrieving content
        retrieved = frappe.get_doc("Site Content", content.name)
        self.assertEqual(retrieved.value, "test_value")
        
        # Cleanup
        frappe.delete_doc("Site Content", content.name)
    
    def test_unique_key_validation(self):
        # Test that duplicate keys are not allowed
        content1 = frappe.get_doc({
            "doctype": "Site Content",
            "key": "duplicate_key",
            "value": "value1",
            "section": "section1",
            "page": "page1"
        })
        content1.insert()
        
        content2 = frappe.get_doc({
            "doctype": "Site Content",
            "key": "duplicate_key",
            "value": "value2",
            "section": "section2",
            "page": "page2"
        })
        
        with self.assertRaises(frappe.ValidationError):
            content2.insert()
        
        # Cleanup
        frappe.delete_doc("Site Content", content1.name)
