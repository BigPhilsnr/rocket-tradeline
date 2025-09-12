# Copyright (c) 2025, RocketTradeline and Contributors
# See license.txt

import frappe
import unittest

class TestAllowedFileName(unittest.TestCase):
    def test_file_name_validation(self):
        """Test file name validation"""
        # Test creating a new allowed file name
        doc = frappe.get_doc({
            "doctype": "Allowed File Name",
            "file_name": "test_file",
            "description": "Test file for validation",
            "category": "Other",
            "is_active": 1
        })
        
        # Should not raise an error
        doc.validate()
        
        # Test duplicate validation would require database operations
        # which are better tested in integration tests
        
    def test_file_name_cleaning(self):
        """Test file name cleaning functionality"""
        doc = frappe.get_doc({
            "doctype": "Allowed File Name",
            "file_name": "Test File Name",
            "description": "Test file cleaning",
            "category": "Other",
            "is_active": 1
        })
        
        doc.validate()
        
        # Should convert to lowercase with underscores
        self.assertEqual(doc.file_name, "test_file_name")