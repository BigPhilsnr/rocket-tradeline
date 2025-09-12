import frappe
from .reports import get_dashboard_reports, get_admin_dashboard

def test_dashboard_api():
    """Test dashboard reports with proper authentication context"""
    try:
        # Set Administrator user context
        frappe.set_user("Administrator")
        
        print("Testing get_dashboard_reports...")
        
        # Test the main dashboard reports function
        result = get_dashboard_reports()
        
        print("Success! Dashboard reports function executed.")
        print(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and result.get("success"):
            print("✅ API returned success=True")
            
            # Check what dashboards were returned
            dashboards = []
            for key in result.keys():
                if key.endswith('_dashboard'):
                    dashboards.append(key)
            
            print(f"Dashboards available: {dashboards}")
            
            # Test admin dashboard specifically
            if 'admin_dashboard' in result:
                admin_data = result['admin_dashboard']
                print(f"Admin dashboard sections: {list(admin_data.keys()) if isinstance(admin_data, dict) else 'Not a dict'}")
                
                # Check overview section
                if 'overview' in admin_data:
                    overview = admin_data['overview']
                    print(f"Overview stats: total_users={overview.get('total_users', 0)}, "
                          f"total_sellers={overview.get('total_sellers', 0)}, "
                          f"total_buyers={overview.get('total_buyers', 0)}, "
                          f"total_brokers={overview.get('total_brokers', 0)}")
                
                # Check tradelines section
                if 'tradelines' in admin_data:
                    tradelines = admin_data['tradelines']
                    print(f"Tradeline stats: total={tradelines.get('total_tradelines', 0)}, "
                          f"active={tradelines.get('active_tradelines', 0)}, "
                          f"remaining_spots={tradelines.get('remaining_spots', 0)}")
                
                # Check financial section
                if 'financial' in admin_data:
                    financial = admin_data['financial']
                    print(f"Financial stats: total_revenue={financial.get('total_revenue', 0)}, "
                          f"monthly_revenue={financial.get('monthly_revenue', 0)}")
        else:
            print("❌ API returned success=False or invalid response")
            print(f"Full response: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}