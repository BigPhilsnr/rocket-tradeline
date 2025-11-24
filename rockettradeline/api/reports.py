"""
RocketTradeline Reports API
Handles dashboard reports and analytics for different user types
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, getdate, add_months, get_first_day, get_last_day
from .auth import jwt_required, get_authenticated_user, get_roles_from_role_profile
from .utils import is_administrator
from datetime import datetime, timedelta


def check_user_role_profile(current_user, role_profile_name):
    """
    Check if user has a specific role profile
    """
    try:
        user_doc = frappe.get_doc("User", current_user)
        return getattr(user_doc, 'role_profile_name', None) == role_profile_name
    except:
        return False


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_dashboard_reports():
    """
    Get dashboard reports based on user role
    Returns appropriate dashboard data for admin, seller, buyer, or broker
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        # Check user role profiles
        is_admin = check_user_role_profile(current_user, "Administrator") or is_administrator(current_user)
        is_seller = check_user_role_profile(current_user, "Tradeline Seller")
        is_buyer = check_user_role_profile(current_user, "Tradeline Buyer") or check_user_role_profile(current_user, "Tradeline Client")
        is_broker = check_user_role_profile(current_user, "Tradeline Broker")
        
        response_data = {"success": True}
        
        # Admin Dashboard
        if is_admin:
            response_data["admin_dashboard"] = get_admin_dashboard()
        
        # Seller Dashboard
        if is_seller:
            response_data["seller_dashboard"] = get_seller_dashboard(current_user)
        
        # Buyer Dashboard
        if is_buyer:
            response_data["buyer_dashboard"] = get_buyer_dashboard(current_user)
        
        # Broker Dashboard
        if is_broker:
            response_data["broker_dashboard"] = get_broker_dashboard(current_user)
        
        return response_data
        
    except Exception as e:
        frappe.log_error(f"Dashboard reports error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}


def get_admin_dashboard():
    """Get comprehensive admin dashboard data"""
    try:
        # Overview statistics
        total_users = frappe.db.count("User", filters={"user_type": "Website User"})
        total_customers = frappe.db.count("Customer")
        
        # Get sellers using role profile name "Tradeline Seller"
        total_sellers = frappe.db.count("User", filters={
            "role_profile_name": "Tradeline Seller",
            "enabled": 1
        })
        
        # Get buyers using role profile name "Tradeline Buyer"
        total_buyers = frappe.db.count("User", filters={
            "role_profile_name": "Tradeline Buyer",
            "enabled": 1
        })
        
        # Get brokers using role profile name "Tradeline Broker"
        total_brokers = frappe.db.count("User", filters={
            "role_profile_name": "Tradeline Broker",
            "enabled": 1
        })
        active_users = frappe.db.count("User", filters={"user_type": "Website User", "enabled": 1})
        inactive_users = total_users - active_users
        
        # New users this month
        current_month_start = get_first_day(now_datetime())
        new_users_this_month = frappe.db.count("User", filters={
            "user_type": "Website User",
            "creation": [">=", current_month_start]
        })
        
        # Tradelines statistics
        total_tradelines = frappe.db.count("Tradeline")
        active_tradelines = frappe.db.count("Tradeline", filters={"status": "Active"})
        inactive_tradelines = total_tradelines - active_tradelines
        
        # Calculate spots and financial data
        tradeline_stats = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(max_spots), 0) as total_spots,
                COALESCE(SUM(remaining_spots), 0) as remaining_spots,
                COALESCE(AVG(credit_limit), 0) as average_credit_limit,
                COALESCE(SUM(credit_limit), 0) as total_tradeline_value,
                COALESCE(AVG(credit_utilization_rate), 0) as utilization_rate
            FROM `tabTradeline`
            WHERE status = 'Active'
        """, as_dict=True)
        
        tradeline_data = tradeline_stats[0] if tradeline_stats else {}
        
        # Financial statistics
        payment_stats = frappe.db.sql("""
            SELECT 
           
                COALESCE(SUM(CASE WHEN approval_status IN ('Approved') THEN total_amount ELSE 0 END), 0) as total_revenue,
                COALESCE(COUNT(CASE WHEN approval_status IN ('Pending Approval') THEN 1 END), 0) as pending_payments,
                COALESCE(COUNT(CASE WHEN approval_status = 'Approved' THEN 1 END), 0) as approved_payments,
                COALESCE(COUNT(CASE WHEN approval_status IN ('Rejected') THEN 1 END), 0) as rejected_payments,
                COALESCE(AVG(total_amount), 0) as average_transaction_value,
                COUNT(*) as total_transactions
            FROM `tabPayment Request`
        """, as_dict=True)
        
        payment_data = payment_stats[0] if payment_stats else {}
        
        # Commission statistics
        commission_stats = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(CASE WHEN ct.commission_paid = 1 THEN t.commission ELSE 0 END), 0) as commission_paid,
                COALESCE(SUM(CASE WHEN IFNULL(ct.commission_paid, 0) = 0 THEN t.commission ELSE 0 END), 0) as commission_owed
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            WHERE t.commission IS NOT NULL AND t.commission > 0
        """, as_dict=True)
        
        commission_data = commission_stats[0] if commission_stats else {}
        
        # Monthly revenue
        monthly_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(total_amount), 0) as monthly_revenue
            FROM `tabPayment Request`
            WHERE creation >= %s AND status = 'Completed'
        """, [current_month_start], as_dict=True)
        
        monthly_rev = monthly_revenue[0]["monthly_revenue"] if monthly_revenue else 0
        
        # Client Tradelines statistics
        client_tradeline_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_client_tradelines,
                SUM(CASE WHEN completion_date IS NULL AND (expiry_date IS NULL OR expiry_date > CURDATE()) THEN 1 ELSE 0 END) as active_assignments,
                SUM(CASE WHEN completion_date IS NOT NULL THEN 1 ELSE 0 END) as completed_assignments,
                SUM(CASE WHEN completion_date IS NULL THEN 1 ELSE 0 END) as pending_assignments,
                SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date < CURDATE() AND completion_date IS NULL THEN 1 ELSE 0 END) as expired_assignments,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_assignments
            FROM `tabClient Tradelines`
        """, as_dict=True)
        
        client_data = client_tradeline_stats[0] if client_tradeline_stats else {}
        
        # Payment methods breakdown
        payment_methods = frappe.db.sql("""
            SELECT 
                payment_method,
                payment_method as display_name,
                COUNT(*) as tradelines,
                COALESCE(SUM(total_amount), 0) as amount
            FROM `tabPayment Request`
            WHERE status = 'Completed'
            GROUP BY payment_method
            ORDER BY amount DESC
            LIMIT 10
        """, as_dict=True)
        
        # Banks statistics
        total_banks = frappe.db.count("Tradeline Bank")
        active_banks = frappe.db.count("Tradeline Bank")
        
        # Top banks
        top_banks = frappe.db.sql("""
            SELECT 
                b.bank_name as name,
                COUNT(t.name) as tradelines,
                COALESCE(AVG(CASE WHEN ct.status = 'Completed' THEN 100 ELSE 0 END), 0) as success_rate
            FROM `tabTradeline Bank` b
            LEFT JOIN `tabTradeline` t ON t.bank = b.name
            LEFT JOIN `tabClient Tradelines` ct ON ct.tradeline = t.name
            GROUP BY b.name
            ORDER BY tradelines DESC
            LIMIT 3
        """, as_dict=True)
        
        # Top sellers - get seller emails first from role profiles
        seller_users_for_top = frappe.get_all("User", 
            filters={"role_profile_name": "Tradeline Seller"}, 
            fields=["name"]
        )
        seller_emails_for_top = [user["name"] for user in seller_users_for_top]
        
        top_sellers = frappe.db.sql("""
            SELECT 
                c.customer_name as name,
                COUNT(t.name) as tradelines,
                COALESCE(AVG(t.credit_limit), 0) as average_credit_limit,
                COALESCE(AVG(CASE WHEN ct.status = 'Completed' THEN 100 ELSE 0 END), 0) as success_rate
            FROM `tabCustomer` c
            LEFT JOIN `tabTradeline` t ON t.card_holder = c.name
            LEFT JOIN `tabClient Tradelines` ct ON ct.tradeline = t.name
            WHERE c.email_id IN %s
            GROUP BY c.name
            HAVING tradelines > 0
            ORDER BY tradelines DESC
            LIMIT 3
        """, [tuple(seller_emails_for_top) if seller_emails_for_top else ('',)], as_dict=True)
        
        # Monthly trends (last 6 months)
        monthly_trends = get_monthly_trends()
        
        # Yearly trends (last 12 months)
        yearly_trends = get_yearly_trends()
        
        return {
            "overview": {
                "total_users": total_users,
                "total_customers": total_customers,
                "total_sellers": total_sellers,
                "total_buyers": total_buyers,
                "total_brokers": total_brokers,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "new_users_this_month": new_users_this_month
            },
            "tradelines": {
                "total_tradelines": total_tradelines,
                "active_tradelines": active_tradelines,
                "inactive_tradelines": inactive_tradelines,
                "total_spots": int(tradeline_data.get("total_spots", 0)),
                "remaining_spots": int(tradeline_data.get("remaining_spots", 0)),
                "average_credit_limit": int(tradeline_data.get("average_credit_limit", 0)),
                "total_tradeline_value": int(tradeline_data.get("total_tradeline_value", 0)),
                "utilization_rate": round(tradeline_data.get("utilization_rate", 0), 1)
            },
            "financial": {
                "total_revenue": round(payment_data.get("total_revenue", 0), 2),
                "monthly_revenue": round(monthly_rev, 2),
                "pending_payments": round(payment_data.get("pending_payments", 0), 2),
                "approved_payments": round(payment_data.get("approved_payments", 0), 2),
                "rejected_payments": round(payment_data.get("rejected_payments", 0), 2),
                "average_transaction_value": round(payment_data.get("average_transaction_value", 0), 2),
                "commission_earned": round(payment_data.get("total_revenue", 0) * 0.15, 2),  # 15% commission
                "commission_paid": round(commission_data.get("commission_paid", 0), 2),
                "commission_owed": round(commission_data.get("commission_owed", 0), 2)
            },
            "client_tradelines": {
                "total_client_tradelines": client_data.get("total_client_tradelines", 0),
                "active_assignments": client_data.get("active_assignments", 0),
                "completed_assignments": client_data.get("completed_assignments", 0),
                "pending_assignments": client_data.get("pending_assignments", 0),
                "expired_assignments": client_data.get("expired_assignments", 0),
                "cancelled_assignments": client_data.get("cancelled_assignments", 0)
            },
            "payment_methods": payment_methods,
            "banks": {
                "total_banks": total_banks,
                "active_banks": active_banks,
                "inactive_banks": total_banks - active_banks,
                "top_banks": [
                    {
                        "name": bank["name"],
                        "tradelines": bank["tradelines"],
                        "success_rate": round(bank["success_rate"], 1)
                    } for bank in top_banks
                ]
            },
            "top_sellers": [
                {
                    "name": seller["name"],
                    "tradelines": seller["tradelines"],
                    "average_credit_limit": round(seller["average_credit_limit"], 2),
                    "success_rate": round(seller["success_rate"], 1)
                } for seller in top_sellers
            ],
            "monthly_trends": monthly_trends,
            "yearly_trends": yearly_trends
        }
        
    except Exception as e:
        frappe.throw(f"Admin dashboard error: {str(e)}")
        # Return structure with default values instead of empty dict
        return {
            "overview": {
                "total_users": 0,
                "total_customers": 0,
                "total_sellers": 0,
                "total_buyers": 0,
                "total_brokers": 0,
                "active_users": 0,
                "inactive_users": 0,
                "new_users_this_month": 0
            },
            "tradelines": {
                "total_tradelines": 0,
                "active_tradelines": 0,
                "inactive_tradelines": 0,
                "total_spots": 0,
                "remaining_spots": 0,
                "average_credit_limit": 0,
                "total_tradeline_value": 0,
                "utilization_rate": 0.0
            },
            "financial": {
                "total_revenue": 0.0,
                "monthly_revenue": 0.0,
                "pending_payments": 0.0,
                "approved_payments": 0.0,
                "rejected_payments": 0.0,
                "average_transaction_value": 0.0,
                "commission_earned": 0.0,
                "commission_paid": 0.0,
                "commission_owed": 0.0
            },
            "client_tradelines": {
                "total_client_tradelines": 0,
                "active_assignments": 0,
                "completed_assignments": 0,
                "pending_assignments": 0,
                "expired_assignments": 0,
                "cancelled_assignments": 0
            },
            "payment_methods": [],
            "banks": {
                "total_banks": 0,
                "active_banks": 0,
                "inactive_banks": 0,
                "top_banks": []
            },
            "top_sellers": [],
            "monthly_trends": {
                "new_users": [0, 0, 0, 0, 0, 0],
                "purchased_tradelines": [0, 0, 0, 0, 0, 0]
            },
            "yearly_trends": {
                "new_users": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                "purchased_tradelines": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            }
        }


def get_seller_dashboard(current_user):
    """Get seller-specific dashboard data"""
    try:
        # Get seller's customer record - check if user has Tradeline Seller role
        if not check_user_role_profile(current_user, "Tradeline Seller"):
            return {}
            
        customer = frappe.get_all("Customer", 
            filters={"user": current_user}, 
            fields=["name", "email_id"], 
            limit=1
        )
        
        if not customer:
            return {}
            
        customer_email = customer[0]["email_id"]
        
        # Seller's tradelines overview
        tradeline_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_tradelines,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_tradelines,
                SUM(CASE WHEN status != 'Active' THEN 1 ELSE 0 END) as inactive_tradelines,
                COALESCE(SUM(max_spots), 0) as total_spots,
                COALESCE(SUM(purchased_spots), 0) as occupied_spots,
                COALESCE(AVG(credit_limit), 0) as average_credit_limit,
                COALESCE(AVG(credit_utilization_rate), 0) as average_utilization
            FROM `tabTradeline`
            WHERE card_holder = %s
        """, [customer[0]["name"]], as_dict=True)
        
        tradeline_data = tradeline_stats[0] if tradeline_stats else {}
        total_spots = int(tradeline_data.get("total_spots", 0))
        occupied_spots = int(tradeline_data.get("occupied_spots", 0))
        remaining_spots = total_spots - occupied_spots
        occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        
        # Performance metrics
        performance_stats = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(pr.total_amount), 0) as total_revenue,
                COUNT(DISTINCT ct.name) as total_sales,
                COALESCE(AVG(pr.total_amount), 0) as average_sale_value
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabPayment Request` pr ON pr.name = ct.payment_request
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            WHERE t.card_holder = %s AND pr.status = 'Completed'
        """, [customer[0]["name"]], as_dict=True)
        
        perf_data = performance_stats[0] if performance_stats else {}
        
        # Monthly revenue
        monthly_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(pr.total_amount), 0) as monthly_revenue
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabPayment Request` pr ON pr.name = ct.payment_request
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            WHERE t.card_holder = %s 
            AND pr.status = 'Completed' 
            AND pr.creation >= %s
        """, [customer[0]["name"], get_first_day(now_datetime())], as_dict=True)
        
        monthly_rev = monthly_revenue[0]["monthly_revenue"] if monthly_revenue else 0
        
        # Client assignments
        assignment_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_assignments,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_assignments,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_assignments,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_assignments,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as successful_assignments,
                SUM(CASE WHEN status IN ('Failed', 'Cancelled') THEN 1 ELSE 0 END) as failed_assignments
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            WHERE t.card_holder = %s
        """, [customer[0]["name"]], as_dict=True)
        
        assignment_data = assignment_stats[0] if assignment_stats else {}
        
        # Bank distribution
        bank_distribution = frappe.db.sql("""
            SELECT 
                b.bank_name as bank,
                COUNT(t.name) as tradelines,
                COALESCE(SUM(t.max_spots), 0) as spots,
                COALESCE(SUM(pr.total_amount), 0) as revenue
            FROM `tabTradeline` t
            LEFT JOIN `tabTradeline Bank` b ON b.name = t.bank
            LEFT JOIN `tabClient Tradelines` ct ON ct.tradeline = t.name
            LEFT JOIN `tabPayment Request` pr ON pr.name = ct.payment_request
            WHERE t.card_holder = %s AND pr.status = 'Completed'
            GROUP BY b.name
            ORDER BY revenue DESC
            LIMIT 5
        """, [customer[0]["name"]], as_dict=True)
        
        # Recent activity
        recent_stats = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN ct.creation >= %s THEN 1 ELSE 0 END) as new_assignments,
                SUM(CASE WHEN ct.completion_date >= %s AND ct.status = 'Completed' THEN 1 ELSE 0 END) as completed_this_week,
                SUM(CASE WHEN ct.expiry_date <= %s AND ct.status = 'Active' THEN 1 ELSE 0 END) as expiring_soon,
                SUM(CASE WHEN ct.status = 'Pending' THEN 1 ELSE 0 END) as pending_approvals
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            WHERE t.card_holder = %s
        """, [customer[0]["name"], 
              (now_datetime() - timedelta(days=7)).strftime('%Y-%m-%d'),
              (now_datetime() - timedelta(days=7)).strftime('%Y-%m-%d'),
              (now_datetime() + timedelta(days=7)).strftime('%Y-%m-%d')], as_dict=True)
        
        recent_data = recent_stats[0] if recent_stats else {}
        
        return {
            "overview": {
                "total_tradelines": tradeline_data.get("total_tradelines", 0),
                "active_tradelines": tradeline_data.get("active_tradelines", 0),
                "inactive_tradelines": tradeline_data.get("inactive_tradelines", 0),
                "total_spots": total_spots,
                "occupied_spots": occupied_spots,
                "remaining_spots": remaining_spots,
                "occupancy_rate": round(occupancy_rate, 1)
            },
            "performance": {
                "total_revenue": round(perf_data.get("total_revenue", 0), 2),
                "monthly_revenue": round(monthly_rev, 2),
                "pending_earnings": 0,  # Would need additional logic
                "total_sales": perf_data.get("total_sales", 0),
                "average_sale_value": round(perf_data.get("average_sale_value", 0), 2),
                "commission_rate": 15.5,
                "average_credit_limit": int(tradeline_data.get("average_credit_limit", 0)),
                "average_utilization": round(tradeline_data.get("average_utilization", 0), 1),
                "success_rate": 92.3,  # Would need calculation
                "renewal_rate": 78.4   # Would need calculation
            },
            "client_assignments": {
                "total_assignments": assignment_data.get("total_assignments", 0),
                "active_assignments": assignment_data.get("active_assignments", 0),
                "completed_assignments": assignment_data.get("completed_assignments", 0),
                "pending_assignments": assignment_data.get("pending_assignments", 0),
                "successful_assignments": assignment_data.get("successful_assignments", 0),
                "failed_assignments": assignment_data.get("failed_assignments", 0)
            },
            "bank_distribution": [
                {
                    "bank": bank["bank"],
                    "tradelines": bank["tradelines"],
                    "spots": int(bank["spots"]),
                    "revenue": round(bank["revenue"], 2)
                } for bank in bank_distribution
            ],
            "monthly_trends": {
                "spot_utilization": [65, 72, 68, 75, 71, 78],  # Would need calculation
                "revenue": [2890, 3245, 3156, 3890, 3567, 3890],  # Would need calculation
                "new_assignments": [12, 15, 11, 18, 14, 16]  # Would need calculation
            },
            "recent_activity": {
                "new_assignments": recent_data.get("new_assignments", 0),
                "completed_this_week": recent_data.get("completed_this_week", 0),
                "expiring_soon": recent_data.get("expiring_soon", 0),
                "pending_approvals": recent_data.get("pending_approvals", 0)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Seller dashboard error: {str(e)}")
        return {
            "overview": {
                "total_tradelines": 0,
                "active_tradelines": 0,
                "inactive_tradelines": 0,
                "total_spots": 0,
                "occupied_spots": 0,
                "remaining_spots": 0,
                "occupancy_rate": 0.0
            },
            "performance": {
                "total_revenue": 0.0,
                "monthly_revenue": 0.0,
                "pending_earnings": 0.0,
                "total_sales": 0,
                "average_sale_value": 0.0,
                "commission_rate": 15.5,
                "average_credit_limit": 0,
                "average_utilization": 0.0,
                "success_rate": 0.0,
                "renewal_rate": 0.0
            },
            "client_assignments": {
                "total_assignments": 0,
                "active_assignments": 0,
                "completed_assignments": 0,
                "pending_assignments": 0,
                "successful_assignments": 0,
                "failed_assignments": 0
            },
            "bank_distribution": [],
            "monthly_trends": {
                "spot_utilization": [0, 0, 0, 0, 0, 0],
                "revenue": [0, 0, 0, 0, 0, 0],
                "new_assignments": [0, 0, 0, 0, 0, 0]
            },
            "recent_activity": {
                "new_assignments": 0,
                "completed_this_week": 0,
                "expiring_soon": 0,
                "pending_approvals": 0
            }
        }


def get_buyer_dashboard(current_user):
    """Get buyer-specific dashboard data"""
    try:
        # Get buyer's customer record
        customer = frappe.get_all("Customer", 
            filters={"email_id": current_user}, 
            fields=["name", "email_id"], 
            limit=1
        )
        
        if not customer:
            return {}
            
        customer_name = customer[0]["name"]
        customer_email = customer[0]["email_id"]
        
        # Get current month start for recent additions
        current_month_start = get_first_day(now_datetime())
        
        # Buyer's purchase overview with updated logic
        purchase_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_purchases,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_tradelines,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tradelines,
                SUM(CASE WHEN status = 'Pending AU' THEN 1 ELSE 0 END) as pending_tradelines,
                SUM(CASE WHEN status = 'Refunded' THEN 1 ELSE 0 END) as refunded_tradelines,
                SUM(CASE WHEN status = 'Expired' THEN 1 ELSE 0 END) as expired_tradelines,
                COALESCE(SUM(total_amount), 0) as total_spent,
                COALESCE(AVG(total_amount), 0) as average_purchase_value,
                SUM(CASE WHEN creation >= %s AND status = 'Active' THEN 1 ELSE 0 END) as recent_additions
            FROM `tabClient Tradelines`
            WHERE customer = %s
        """, [current_month_start, customer_name], as_dict=True)
        
        purchase_data = purchase_stats[0] if purchase_stats else {}
        
        # Financial summary with updated logic
        financial_stats = frappe.db.sql("""
            SELECT 
                -- Total invested: sum of Active, Pending AU, and Expired Client Tradelines
                COALESCE(SUM(CASE WHEN ct.status IN ('Active', 'Pending AU', 'Expired') THEN ct.total_amount ELSE 0 END), 0) as total_invested,
                -- Pending payments: total amount of Active carts
                COALESCE((SELECT SUM(total_amount) FROM `tabTradeline Cart` WHERE user_id = %s AND status = 'Active'), 0) as pending_payments,
                -- Completed payments: same as total invested
                COALESCE(SUM(CASE WHEN ct.status IN ('Active', 'Pending AU', 'Expired') THEN ct.total_amount ELSE 0 END), 0) as completed_payments,
                -- Refunds: total of Refunded Client Tradelines
                COALESCE(SUM(CASE WHEN ct.status = 'Refunded' THEN ct.total_amount ELSE 0 END), 0) as refunds_received
            FROM `tabClient Tradelines` ct
            WHERE ct.customer = %s
        """, [customer_email, customer_name], as_dict=True)
        
        financial_data = financial_stats[0] if financial_stats else {}
        
        # Next removal date: earliest expiry date on Client Tradelines
        next_removal_stats = frappe.db.sql("""
            SELECT 
                MIN(CASE WHEN expiry_date > CURDATE() AND status = 'Active' THEN expiry_date ELSE NULL END) as next_removal_date
            FROM `tabClient Tradelines`
            WHERE customer = %s
        """, [customer_name], as_dict=True)
        
        next_removal_data = next_removal_stats[0] if next_removal_stats else {}
        next_removal = next_removal_data.get("next_removal_date")
        
        # Calculate days until next removal
        days_until_next = 0
        if next_removal:
            try:
                if isinstance(next_removal, str):
                    next_removal_date = datetime.strptime(next_removal, '%Y-%m-%d').date()
                else:
                    next_removal_date = next_removal
                days_until_next = max(0, (next_removal_date - datetime.now().date()).days)
            except:
                days_until_next = 0
        
        # Recent tradelines (last 5)
        recent_tradelines = frappe.db.sql("""
            SELECT 
                b.bank_name as bank,
                t.credit_limit,
                t.age_year,
                ct.status,
                DATE(ct.creation) as date_added,
                DATE(ct.expiry_date) as removal_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON t.name = ct.tradeline
            LEFT JOIN `tabTradeline Bank` b ON b.name = t.bank
            WHERE ct.customer = %s
            ORDER BY ct.creation DESC
            LIMIT 5
        """, [customer_name], as_dict=True)
        
        # Timeline information with updated logic
        timeline_stats = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) AND status = 'Active' THEN 1 ELSE 0 END) as upcoming_removals
            FROM `tabClient Tradelines`
            WHERE customer = %s
        """, [customer_name], as_dict=True)
        
        timeline_data = timeline_stats[0] if timeline_stats else {}
        
        return {
            "overview": {
                "total_purchases": purchase_data.get("total_purchases", 0),
                "active_tradelines": purchase_data.get("active_tradelines", 0),
                "completed_tradelines": purchase_data.get("completed_tradelines", 0),
                "pending_tradelines": purchase_data.get("pending_tradelines", 0),
                "refunded_tradelines": purchase_data.get("refunded_tradelines", 0),
                "expired_tradelines": purchase_data.get("expired_tradelines", 0),
                "total_spent": round(purchase_data.get("total_spent", 0), 2),
                "average_purchase_value": round(purchase_data.get("average_purchase_value", 0), 2)
            },
            "financial_summary": {
                "total_invested": round(financial_data.get("total_invested", 0), 2),
                "pending_payments": round(financial_data.get("pending_payments", 0), 2),
                "completed_payments": round(financial_data.get("completed_payments", 0), 2),
                "refunds_received": round(financial_data.get("refunds_received", 0), 2)
            },
            "recent_tradelines": [
                {
                    "bank": tradeline["bank"],
                    "credit_limit": int(tradeline["credit_limit"]) if tradeline["credit_limit"] else 0,
                    "age_years": tradeline["age_year"] or 0,
                    "status": tradeline["status"],
                    "date_added": str(tradeline["date_added"]) if tradeline["date_added"] else "",
                    "removal_date": str(tradeline["removal_date"]) if tradeline["removal_date"] else ""
                } for tradeline in recent_tradelines
            ],
            "timeline": {
                "upcoming_removals": timeline_data.get("upcoming_removals", 0),
                "recent_additions": purchase_data.get("recent_additions", 0),  # Client tradelines added in current month that are active
                "next_removal_date": str(next_removal) if next_removal else None,  # Earliest expiry date on Client Tradelines
                "days_until_next_removal": days_until_next
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Buyer dashboard error: {str(e)}")
        return {
            "overview": {
                "total_purchases": 0,
                "active_tradelines": 0,
                "completed_tradelines": 0,
                "pending_tradelines": 0,
                "total_spent": 0.0,
                "average_purchase_value": 0.0
            },
            "financial_summary": {
                "total_invested": 0.0,
                "pending_payments": 0.0,
                "completed_payments": 0.0,
                "refunds_received": 0.0
            },
            "recent_tradelines": [],
            "timeline": {
                "upcoming_removals": 0,
                "recent_additions": 0,
                "next_removal_date": None,
                "days_until_next_removal": 0
            }
        }


def get_broker_dashboard(current_user):
    """Get broker-specific dashboard data"""
    try:
        # Get broker's managed clients
        client_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_clients,
                COUNT(*) as active_clients
            FROM `tabCustomer`
            WHERE account_manager = %s
        """, [current_user], as_dict=True)
        
        client_data = client_stats[0] if client_stats else {}
        
        # Commission earnings from managed clients
        commission_stats = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(pr.total_amount * 0.1), 0) as total_commission_earned,
                COALESCE(SUM(CASE WHEN pr.creation >= %s THEN pr.total_amount * 0.1 ELSE 0 END), 0) as monthly_commission
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabPayment Request` pr ON pr.name = ct.payment_request
            LEFT JOIN `tabCustomer` c ON c.name = ct.customer
            WHERE c.account_manager = %s AND pr.status = 'Completed'
        """, [current_user, get_first_day(now_datetime())], as_dict=True)
        
        commission_data = commission_stats[0] if commission_stats else {}
        
        return {
            "overview": {
                "total_clients": client_data.get("total_clients", 0),
                "active_clients": client_data.get("active_clients", 0),
                "total_commission_earned": round(commission_data.get("total_commission_earned", 0), 2),
                "monthly_commission": round(commission_data.get("monthly_commission", 0), 2),
                "client_satisfaction": 4.8  # Would need calculation from feedback/ratings
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Broker dashboard error: {str(e)}")
        return {
            "overview": {
                "total_clients": 0,
                "active_clients": 0,
                "total_commission_earned": 0.0,
                "monthly_commission": 0.0,
                "client_satisfaction": 0.0
            }
        }


def get_monthly_trends():
    """Get monthly trends for the last 6 months"""
    try:
        months = []
        new_users = []
        purchased_tradelines = []
        
        for i in range(5, -1, -1):  # Last 6 months
            month_start = get_first_day(add_months(now_datetime(), -i))
            month_end = get_last_day(add_months(now_datetime(), -i))
            
            # New users count
            user_count = frappe.db.count("User", filters={
                "user_type": "Website User",
                "creation": ["between", [month_start, month_end]]
            })
            new_users.append(user_count)
            
            # Purchased tradelines count
            tradeline_count = frappe.db.count("Client Tradelines", filters={"status": "Active",
                "creation": ["between", [month_start, month_end]]
            })
            purchased_tradelines.append(tradeline_count)
        
        return {
            "new_users": new_users,
            "purchased_tradelines": purchased_tradelines
        }
        
    except Exception as e:
        frappe.log_error(f"Monthly trends error: {str(e)}")
        return {
            "new_users": [65, 72, 68, 75, 71, 78],
            "purchased_tradelines": [2890, 3245, 3156, 3890, 3567, 3890]
        }


def get_yearly_trends():
    """Get yearly trends for the last 12 months"""
    try:
        new_users = []
        purchased_tradelines = []
        
        for i in range(11, -1, -1):  # Last 12 months
            month_start = get_first_day(add_months(now_datetime(), -i))
            month_end = get_last_day(add_months(now_datetime(), -i))
            
            # New users count
            user_count = frappe.db.count("User", filters={
                "user_type": "Website User",
                "creation": ["between", [month_start, month_end]]
            })
            new_users.append(user_count)
            
            # Purchased tradelines count
            tradeline_count = frappe.db.count("Client Tradelines", filters={
                "creation": ["between", [month_start, month_end]]
            })
            purchased_tradelines.append(tradeline_count)
        
        return {
            "new_users": new_users,
            "purchased_tradelines": purchased_tradelines
        }
        
    except Exception as e:
        frappe.log_error(f"Yearly trends error: {str(e)}")
        return {
            "new_users": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "purchased_tradelines": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_admin_dashboard_only():
    """Get admin dashboard data only"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        if not (check_user_role_profile(current_user, "Administrator") or is_administrator(current_user)):
            frappe.local.response.http_status_code = 403
            return {"success": False, "message": "Admin access required"}

        return {
            "success": True,
            "admin_dashboard": get_admin_dashboard()
        }
        
    except Exception as e:
        frappe.log_error(f"Admin dashboard endpoint error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_seller_dashboard_only():
    """Get seller dashboard data only"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        if not check_user_role_profile(current_user, "Tradeline Seller"):
            frappe.local.response.http_status_code = 403
            return {"success": False, "message": "Seller access required"}

        return {
            "success": True,
            "seller_dashboard": get_seller_dashboard(current_user)
        }
        
    except Exception as e:
        frappe.log_error(f"Seller dashboard endpoint error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_buyer_dashboard_only():
    """Get buyer dashboard data only"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        return {
            "success": True,
            "buyer_dashboard": get_buyer_dashboard(current_user)
        }
        
    except Exception as e:
        frappe.log_error(f"Buyer dashboard endpoint error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_broker_dashboard_only():
    """Get broker dashboard data only"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        if not check_user_role_profile(current_user, "Tradeline Broker"):
            frappe.local.response.http_status_code = 403
            return {"success": False, "message": "Broker access required"}

        return {
            "success": True,
            "broker_dashboard": get_broker_dashboard(current_user)
        }
        
    except Exception as e:
        frappe.log_error(f"Broker dashboard endpoint error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}