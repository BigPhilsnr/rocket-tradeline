#!/usr/bin/env python3
"""
Transfer Allowed File Name Doctype
Wrapper script to transfer the Allowed File Name doctype
"""

import frappe
from .transfer_doctype import transfer_doctype

def execute():
    """Execute the transfer for Allowed File Name doctype"""
    try:
        print("Starting transfer of Allowed File Name doctype...")
        result = transfer_doctype("Allowed File Name")
        print("Transfer completed successfully!")
        return result
    except Exception as e:
        print(f"Transfer failed: {str(e)}")
        frappe.log_error(f"Allowed File Name transfer failed: {str(e)}")
        raise

if __name__ == "__main__":
    execute()