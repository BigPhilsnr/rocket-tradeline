#!/usr/bin/env python3
"""
Fix OAuth callback issues for Connected Apps
"""

import frappe
from frappe import whitelist


def fix_oauth_callback():
    """
    Add the Connected App callback to ignored routes for CSRF
    """
    try:
        # Check current ignored routes
        ignored_routes = frappe.get_hooks('ignore_csrf')
        
        callback_route = "frappe.integrations.doctype.connected_app.connected_app.callback"
        
        if callback_route not in ignored_routes:
            print(f"OAuth callback route needs to be whitelisted: {callback_route}")
            
        # Show current webhook settings
        webhooks = frappe.get_all('Webhook', fields=['name', 'webhook_url', 'enabled'])
        print(f"Current webhooks: {webhooks}")
        
        # Check Connected App settings
        connected_apps = frappe.get_all('Connected App', fields=['name', 'provider_name', 'client_id'])
        print(f"Connected Apps: {connected_apps}")
        
        frappe.msgprint(f"OAuth callback analysis complete. Found {len(connected_apps)} Connected Apps.")
        
    except Exception as e:
        frappe.throw(f"Failed to analyze OAuth callback: {str(e)}")


@whitelist(allow_guest=True)
def test_callback_access():
    """Test if callback can be accessed"""
    return {"status": "success", "message": "Callback endpoint is accessible"}


def check_app_hooks():
    """Check what hooks are defined in the app"""
    try:
        from rockettradeline import hooks
        
        # Check if ignore_csrf is defined
        if hasattr(hooks, 'ignore_csrf'):
            print(f"Current ignore_csrf hooks: {hooks.ignore_csrf}")
        else:
            print("No ignore_csrf hooks found in app")
            
        # Check other relevant hooks
        relevant_hooks = ['ignore_csrf', 'before_request', 'after_request']
        for hook in relevant_hooks:
            if hasattr(hooks, hook):
                print(f"{hook}: {getattr(hooks, hook)}")
                
        frappe.msgprint("App hooks analysis complete")
        
    except Exception as e:
        frappe.throw(f"Failed to check app hooks: {str(e)}")