#!/usr/bin/env python3
"""
Compare roles between external and current database
"""

import frappe
import pymysql


def compare_roles():
    """Compare roles between external and current database"""
    try:
        # Get external roles
        connection = pymysql.connect(
            host='142.132.165.13',
            port=3306,
            user='external_user',
            password='SecurePassword123!',
            database='_9ee58f4274d12503',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM tabRole ORDER BY name")
            external_roles = [row['name'] for row in cursor.fetchall()]
        
        connection.close()
        
        # Get current roles
        current_roles = frappe.get_all('Role', fields=['name'], order_by='name')
        current_role_names = [role['name'] for role in current_roles]
        
        # Find differences
        missing_in_current = set(external_roles) - set(current_role_names)
        missing_in_external = set(current_role_names) - set(external_roles)
        
        result = {
            'external_count': len(external_roles),
            'current_count': len(current_role_names),
            'missing_in_current': list(missing_in_current),
            'missing_in_external': list(missing_in_external),
            'common_roles': len(set(external_roles) & set(current_role_names))
        }
        
        print(f"External DB has {result['external_count']} roles")
        print(f"Current DB has {result['current_count']} roles")
        print(f"Common roles: {result['common_roles']}")
        
        if missing_in_current:
            print(f"Missing in current DB: {missing_in_current}")
        
        if missing_in_external:
            print(f"Missing in external DB: {missing_in_external}")
        
        frappe.msgprint(f"Role comparison complete. External: {result['external_count']}, Current: {result['current_count']}, Common: {result['common_roles']}")
        
        return result
        
    except Exception as e:
        frappe.throw(f"Failed to compare roles: {str(e)}")


def show_role_profile_summary():
    """Show summary of transferred Role Profiles"""
    try:
        profiles = frappe.get_all('Role Profile', fields=['name', 'role_profile'])
        
        for profile in profiles:
            roles = frappe.get_all('Has Role', 
                filters={'parent': profile['name'], 'parenttype': 'Role Profile'},
                fields=['role']
            )
            print(f"\n{profile['name']} Profile:")
            print(f"  Roles: {[r['role'] for r in roles]}")
        
        frappe.msgprint(f"Found {len(profiles)} Role Profiles with their associated roles")
        
    except Exception as e:
        frappe.throw(f"Failed to show role profile summary: {str(e)}")