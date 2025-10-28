# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, getdate, add_days
from rockettradeline.api.auth import get_email_header, get_email_footer
from frappe.email.queue import flush
from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template


def check_and_expire_client_tradelines():
    """
    Cron job to check for expired client tradelines and update their status
    Runs every hour to check for expired tradelines
    Note: Clients receive expiry reminder 7 days in advance via check_and_send_expiry_reminders()
    Note: Cardholder notifications are sent 1 day after expiry via check_and_send_cardholder_removal_notifications()
    """
    try:
        # Use safer logging that doesn't require file permissions
        print("Starting expired client tradelines check...")
        
        # Get current date
        current_date = getdate()
        
        # Find all active client tradelines that have expired
        expired_query = """
            SELECT 
                ct.name,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.expiry_date,
                ct.total_amount,
                ct.quantity,
                ct.unit_price,
                ct.completion_date,
                ct.notes,
                t.name as tradeline_id,
                t.bank,
                tb.bank_name,
                t.card_holder,
                c.email_id as client_email,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                t.price as tradeline_price
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.status = 'Active'
            AND ct.expiry_date IS NOT NULL
            AND ct.expiry_date <= %s
        """
        
        expired_tradelines = frappe.db.sql(expired_query, (current_date,), as_dict=True)
        
        if not expired_tradelines:
            print("No expired client tradelines found.")
            return {"success": True, "message": "No expired tradelines found", "processed": 0}
        
        processed_count = 0
        email_failures = []
        
        for tradeline in expired_tradelines:
            try:
                # Update client tradeline status to Expired
                frappe.db.set_value("Client Tradelines", tradeline.name, "status", "Expired")
                
                processed_count += 1
                print(f"Processed expired tradeline: {tradeline.name} - status updated to Expired")
                
            except Exception as e:
                error_msg = f"Failed to process tradeline {tradeline.name}: {str(e)}"
                frappe.log_error(error_msg, "Expired Tradeline Processing Error")
                email_failures.append({"tradeline": tradeline.name, "error": str(e)})
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Processed {processed_count} expired tradelines",
            "processed": processed_count,
            "total_found": len(expired_tradelines)
        }
        
        if email_failures:
            result["email_failures"] = email_failures
        
        print(f"Expired tradelines check completed. Processed: {processed_count}")
        return result
        
    except Exception as e:
        error_msg = f"Expired tradelines cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Expired Tradelines Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


def send_cardholder_removal_notification(tradeline):
    """
    Send email notification to cardholder to remove the client from tradeline
    """
    try:
        if not tradeline.cardholder_email:
            return
        
        # Prepare simplified template parameters
        template_params = {
            "cardholder_name": tradeline.cardholder_name or 'Card Holder',
            "customer_name": tradeline.customer_name,
            "bank_name": tradeline.bank_name or 'N/A',
            "credit_limit": f"{tradeline.credit_limit:,.0f}" if tradeline.credit_limit else "N/A",
            "age_year": tradeline.age_year or 0
        }
        
        # Send email using template
        send_email_template(
            template_name="Cardholder Removal Required",
            recipients=[tradeline.cardholder_email],
            parameters=template_params
        )
        
        print(f"Cardholder removal notification sent to {tradeline.cardholder_email} for tradeline {tradeline.name}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send cardholder removal notification: {str(e)}", "Cardholder Notification Error")


def send_client_expiration_notification(tradeline):
    """
    Send email notification to client about tradeline expiration
    """
    try:
        # Get customer document to check for account_manager
        customer_doc = frappe.get_doc("Customer", tradeline.customer)
        recipient_email = customer_doc.account_manager if customer_doc.account_manager else tradeline.client_email
        
        if not recipient_email:
            return
        
        # Calculate service duration
        service_duration = "N/A"
        if tradeline.completion_date and tradeline.expiry_date:
            service_duration = str((getdate(tradeline.expiry_date) - getdate(tradeline.completion_date)).days)
        
        # Prepare template parameters
        template_params = {
            "customer_name": tradeline.customer_name,
            "tradeline_id": tradeline.name,
            "bank_name": tradeline.bank_name or 'N/A',
            "credit_limit": f"{tradeline.credit_limit:,.0f}" if tradeline.credit_limit else "N/A",
            "age_year": tradeline.age_year or 0,
            "age_month": tradeline.age_month or 0,
            "completion_date": tradeline.completion_date or 'N/A',
            "expiry_date": str(tradeline.expiry_date),
            "total_amount": f"{tradeline.total_amount:,.2f}" if tradeline.total_amount else "0.00",
            "service_duration": service_duration,
            "quantity": tradeline.quantity or 1
        }
        
        # Send email using template
        send_email_template(
            template_name="Client Tradeline Expiration",
            recipients=[recipient_email],
            parameters=template_params
        )
        
        print(f"Client expiration notification sent to {recipient_email} for tradeline {tradeline.name}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send client expiration notification: {str(e)}", "Client Notification Error")


def check_and_send_cardholder_removal_notifications():
    """
    Cron job to send cardholder removal notifications for tradelines that expired yesterday
    Runs daily to notify cardholders to remove AUs 1 day after expiry
    """
    try:
        print("Starting cardholder removal notifications check...")
        
        # Get yesterday's date
        yesterday = add_days(getdate(), -1)
        
        print(f"Checking for tradelines that expired on {yesterday}")
        
        # Find all expired client tradelines where expiry date was yesterday
        expired_yesterday_query = """
            SELECT 
                ct.name,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.expiry_date,
                t.name as tradeline_id,
                t.bank,
                tb.bank_name,
                t.card_holder,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.status = 'Expired'
            AND ct.expiry_date = %s
        """
        
        expired_yesterday = frappe.db.sql(expired_yesterday_query, (yesterday,), as_dict=True)
        
        if not expired_yesterday:
            print(f"No tradelines expired on {yesterday}.")
            return {"success": True, "message": f"No tradelines expired on {yesterday}", "processed": 0}
        
        print(f"Found {len(expired_yesterday)} tradelines that expired yesterday")
        
        processed_count = 0
        email_failures = []
        
        for tradeline in expired_yesterday:
            try:
                # Send notification to cardholder
                if tradeline.cardholder_email:
                    send_cardholder_removal_notification(tradeline)
                    processed_count += 1
                    print(f"Cardholder removal notification sent to {tradeline.cardholder_email} for tradeline {tradeline.name}")
                else:
                    print(f"Warning: No cardholder email found for tradeline {tradeline.name}")
                    
            except Exception as e:
                error_msg = f"Failed to send cardholder notification for {tradeline.name}: {str(e)}"
                frappe.log_error(error_msg, "Cardholder Removal Notification Error")
                email_failures.append({"tradeline": tradeline.name, "error": str(e)})
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Sent cardholder removal notifications for {processed_count} tradelines",
            "processed": processed_count,
            "total_found": len(expired_yesterday),
            "expiry_date": str(yesterday)
        }
        
        if email_failures:
            result["email_failures"] = email_failures
        
        print(f"Cardholder removal notifications completed. Sent {processed_count} notifications.")
        return result
        
    except Exception as e:
        error_msg = f"Cardholder removal notifications cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Cardholder Removal Notifications Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def manual_expire_tradelines_check():
    """
    Manual trigger for expired tradelines check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        result = check_and_expire_client_tradelines()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual expired tradelines check failed: {str(e)}")


@frappe.whitelist()
def manual_check_cardholder_removals():
    """
    Manual trigger for cardholder removal notifications check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        result = check_and_send_cardholder_removal_notifications()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual cardholder removal notifications check failed: {str(e)}")


@frappe.whitelist()
def get_expiring_tradelines(days_ahead=7):
    """
    Get tradelines that will expire within specified days (for monitoring)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        future_date = add_days(getdate(), int(days_ahead))
        
        expiring_query = """
            SELECT 
                ct.name,
                ct.customer_name,
                ct.tradeline_name,
                ct.expiry_date,
                ct.total_amount,
                tb.bank_name,
                c.email_id as client_email,
                ch.email_id as cardholder_email,
                DATEDIFF(ct.expiry_date, CURDATE()) as days_until_expiry
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.status = 'Active'
            AND ct.expiry_date IS NOT NULL
            AND ct.expiry_date <= %s
            AND ct.expiry_date >= CURDATE()
            ORDER BY ct.expiry_date ASC
        """
        
        expiring_tradelines = frappe.db.sql(expiring_query, (future_date,), as_dict=True)
        
        return {
            "success": True,
            "expiring_tradelines": expiring_tradelines,
            "total": len(expiring_tradelines),
            "days_ahead": int(days_ahead)
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch expiring tradelines: {str(e)}")


def process_email_queue():
    """
    Process unsent emails in the email queue
    Runs every minute to ensure emails are sent promptly
    """
    try:
        # Use safer logging that doesn't require file permissions
        print("Starting email queue processing...")
        
        # Get count of pending emails before processing
        pending_count = frappe.db.count("Email Queue", filters={
            "status": "Not Sent"
        })
        
        if pending_count == 0:
            print("No pending emails in queue")
            return {"success": True, "message": "No pending emails", "processed": 0}
        
        print(f"Found {pending_count} pending emails in queue")
        
        # Process the email queue using Frappe's built-in flush function
        flush()
        
        # Get count of remaining emails after processing
        remaining_count = frappe.db.count("Email Queue", filters={
            "status": "Not Sent"
        })
        
        processed_count = pending_count - remaining_count
        
        if processed_count > 0:
            print(f"Successfully processed {processed_count} emails from queue")
        
        # Commit the transaction
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Processed {processed_count} emails",
            "processed": processed_count,
            "remaining": remaining_count,
            "total_found": pending_count
        }
        
    except Exception as e:
        error_msg = f"Email queue processing failed: {str(e)}"
        # Use frappe.log_error which is safer than frappe.logger()
        frappe.log_error(error_msg, "Email Queue Processing Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def manual_process_email_queue():
    """
    Manual trigger for email queue processing (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        result = process_email_queue()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual email queue processing failed: {str(e)}")


def check_and_send_closing_date_notifications():
    """
    Cron job to check for tradelines that passed their closing date 2 days ago
    and send notifications to clients
    Runs daily to check for closing dates
    """
    try:
        print("Starting closing date notifications check...")
        
        # Get current date and calculate target date (2 days ago)
        current_date = getdate()
        target_date = add_days(current_date, -2)  # 2 days before today
        
        # Extract year, month, and day from target date
        target_year = target_date.year
        target_month = target_date.month
        target_day = target_date.day
        
        print(f"Checking for tradelines with closing date on {target_date} (2 days ago)")
        
        # Find all active client tradelines where the closing date was 2 days ago
        closing_query = """
            SELECT DISTINCT
                ct.name as client_tradeline_id,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.total_amount,
                ct.quantity,
                ct.completion_date,
                ct.expiry_date,
                t.name as tradeline_id,
                t.bank,
                tb.bank_name,
                t.card_holder,
                c.email_id as client_email,
                COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                c.customer_name as client_full_name,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                t.price as tradeline_price,
                CASE 
                    WHEN t.closing_date IS NOT NULL AND t.closing_date != '' THEN
                        DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0')))
                    ELSE NULL
                END as calculated_closing_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.status = 'Active'
            AND t.closing_date IS NOT NULL
            AND t.closing_date != ''
            AND CAST(t.closing_date AS UNSIGNED) BETWEEN 1 AND 31
            AND DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0'))) = %s
        """
        
        closing_tradelines = frappe.db.sql(closing_query, (
            target_year, target_month,  # For calculated_closing_date
            target_year, target_month, target_date  # For WHERE condition
        ), as_dict=True)
        
        if not closing_tradelines:
            # If no exact matches found, check for tradelines with invalid closing dates (e.g., day 31 in a 30-day month)
            # and find the closest valid date
            closest_date_query = """
                SELECT DISTINCT
                    ct.name as client_tradeline_id,
                    ct.customer,
                    ct.customer_name,
                    ct.tradeline,
                    ct.tradeline_name,
                    ct.total_amount,
                    ct.quantity,
                    ct.completion_date,
                    ct.expiry_date,
                    t.name as tradeline_id,
                    t.bank,
                    tb.bank_name,
                    t.card_holder,
                    c.email_id as client_email,
                    COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                    c.customer_name as client_full_name,
                    ch.email_id as cardholder_email,
                    ch.customer_name as cardholder_name,
                    t.credit_limit,
                    t.age_year,
                    t.age_month,
                    t.closing_date,
                    t.price as tradeline_price,
                    LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01')) as month_last_day
                FROM `tabClient Tradelines` ct
                LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
                LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
                LEFT JOIN `tabCustomer` c ON ct.customer = c.name
                LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
                WHERE ct.status = 'Active'
                AND t.closing_date IS NOT NULL
                AND t.closing_date != ''
                AND CAST(t.closing_date AS UNSIGNED) > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01')))
                AND DATE(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) = %s
            """
            
            closest_tradelines = frappe.db.sql(closest_date_query, (
                target_year, target_month,  # For month_last_day calculation
                target_year, target_month,  # For CAST comparison
                target_year, target_month, target_date  # For WHERE condition
            ), as_dict=True)
            
            if closest_tradelines:
                print(f"Found {len(closest_tradelines)} tradelines with invalid closing dates, using closest date.")
                closing_tradelines = closest_tradelines
            else:
                print(f"No tradelines with closing date 2 days ago ({target_date}) found.")
                return {"success": True, "message": f"No tradelines closing on {target_date}", "processed": 0}
        
        processed_count = 0
        email_failures = []
        
        # Group tradelines by customer email to send consolidated emails
        customer_tradelines = {}
        for tradeline in closing_tradelines:
            recipient_email = tradeline.client_email_recipient if hasattr(tradeline, 'client_email_recipient') else tradeline.client_email
            if recipient_email:
                if recipient_email not in customer_tradelines:
                    customer_tradelines[recipient_email] = {
                        'customer_name': tradeline.client_full_name or tradeline.customer_name,
                        'tradelines': []
                    }
                customer_tradelines[recipient_email]['tradelines'].append(tradeline)
        
        # Send emails to each customer
        for client_email, customer_data in customer_tradelines.items():
            try:
                send_closing_date_notification(client_email, customer_data)
                processed_count += 1
                print(f"Closing date notification sent to {client_email}")
                
            except Exception as e:
                error_msg = f"Failed to send closing date notification to {client_email}: {str(e)}"
                frappe.log_error(error_msg, "Closing Date Notification Error")
                email_failures.append({"email": client_email, "error": str(e)})
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Sent closing date notifications to {processed_count} customers",
            "processed": processed_count,
            "total_tradelines": len(closing_tradelines),
            "target_closing_date": str(target_date),
            "days_after_closing": 2
        }
        
        if email_failures:
            result["email_failures"] = email_failures
        
        print(f"Closing date notifications completed. Sent to {processed_count} customers.")
        return result
        
    except Exception as e:
        error_msg = f"Closing date notifications cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Closing Date Notifications Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


def send_closing_date_notification(client_email, customer_data):
    """
    Send closing date notification email to client
    """
    try:
        if not client_email:
            return
        
        customer_name = customer_data['customer_name']
        tradelines = customer_data['tradelines']
        
        # Build tradelines HTML using simple div-based layout
        tradelines_html = ""
        for tl in tradelines:
            bank_name = tl.bank_name or 'N/A'
            age_year = tl.age_year or 0
            credit_limit = f"{tl.credit_limit:,.0f}" if tl.credit_limit else "N/A"
            closing_date = tl.closing_date or 'N/A'
            customer_name = tl.customer_name
            
            tradelines_html += f"""
                    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 15px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <div style="font-weight: 600; color: #374151; font-size: 15px;">{age_year} Year {bank_name}</div>
                            <div style="color: #17B26A; font-weight: 600;">${credit_limit}</div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 14px; color: #6b7280;">
                            <div><strong>Close Date:</strong> {closing_date}</div>
                            <div><strong>AU:</strong> {customer_name}</div>
                        </div>
                    </div>"""
        
        # Prepare template parameters
        template_params = {
            "customer_name": customer_name,
            "tradelines_html": tradelines_html,
            "tradelines_count": len(tradelines),
            "client_email": client_email
        }
        
        # Send email using Email Template Custom system
        send_email_template(
            template_name="Tradeline Closing Date Notification",
            recipients=[client_email],
            parameters=template_params
        )
        
        print(f"Closing date notification sent to {client_email}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send closing date notification to {client_email}: {str(e)}", "Closing Date Notification Error")
        raise e


@frappe.whitelist()
def manual_check_closing_dates():
    """
    Manual trigger for closing date notifications check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        result = check_and_send_closing_date_notifications()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual closing date check failed: {str(e)}")


@frappe.whitelist()
def get_todays_closing_tradelines():
    """
    Get tradelines that will trigger notifications today (closing date was 2 days ago)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        current_date = getdate()
        target_date = add_days(current_date, -2)  # 2 days ago
        target_year = target_date.year
        target_month = target_date.month
        
        # Get tradelines with exact closing date match (2 days ago)
        closing_query = """
            SELECT 
                ct.name as client_tradeline_id,
                ct.customer_name,
                ct.tradeline_name,
                tb.bank_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                c.email_id as client_email,
                COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0'))) as calculated_closing_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Active'
            AND t.closing_date IS NOT NULL
            AND t.closing_date != ''
            AND CAST(t.closing_date AS UNSIGNED) BETWEEN 1 AND 31
            AND DATE(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-', LPAD(t.closing_date, 2, '0'))) = %s
            ORDER BY c.email_id, tb.bank_name
        """
        
        closing_tradelines = frappe.db.sql(closing_query, (
            target_year, target_month,  # For calculated_closing_date
            target_year, target_month, target_date  # For WHERE condition
        ), as_dict=True)
        
        # Also get tradelines with invalid dates that fall to target date (closest date logic)
        if not closing_tradelines:
            closest_query = """
                SELECT 
                    ct.name as client_tradeline_id,
                    ct.customer_name,
                    ct.tradeline_name,
                    tb.bank_name,
                    t.credit_limit,
                    t.age_year,
                    t.age_month,
                    t.closing_date,
                    c.email_id as client_email,
                    COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                    LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01')) as calculated_closing_date,
                    'closest_date' as match_type
                FROM `tabClient Tradelines` ct
                LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
                LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
                LEFT JOIN `tabCustomer` c ON ct.customer = c.name
                WHERE ct.status = 'Active'
                AND t.closing_date IS NOT NULL
                AND t.closing_date != ''
                AND CAST(t.closing_date AS UNSIGNED) > DAY(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01')))
                AND DATE(LAST_DAY(CONCAT(%s, '-', LPAD(%s, 2, '0'), '-01'))) = %s
                ORDER BY c.email_id, tb.bank_name
            """
            
            closing_tradelines = frappe.db.sql(closest_query, (
                target_year, target_month,  # For calculated_closing_date
                target_year, target_month,  # For CAST comparison
                target_year, target_month, target_date  # For WHERE condition
            ), as_dict=True)
        
        return {
            "success": True,
            "closing_tradelines": closing_tradelines,
            "total": len(closing_tradelines),
            "current_date": str(current_date),
            "target_date": str(target_date),
            "days_after_closing": 2,
            "target_year": target_year,
            "target_month": target_month
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch today's closing tradelines: {str(e)}")


def check_and_send_expiry_reminders():
    """
    Cron job to check for client tradelines expiring within 7 days
    and send reminder notifications to clients
    Runs daily to check for upcoming expiries
    """
    try:
        print("Starting tradeline expiry reminder check...")
        
        # Get current date and 7 days ahead
        current_date = getdate()
        expiry_threshold_date = add_days(current_date, 7)
        
        print(f"Checking for tradelines expiring between {current_date} and {expiry_threshold_date}")
        
        # Find all active client tradelines that will expire within 7 days
        expiring_query = """
            SELECT DISTINCT
                ct.name as client_tradeline_id,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.total_amount,
                ct.quantity,
                ct.completion_date,
                ct.expiry_date,
                t.name as tradeline_id,
                t.bank,
                tb.bank_name,
                t.card_holder,
                c.email_id as client_email,
                COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                c.customer_name as client_full_name,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                t.price as tradeline_price,
                DATEDIFF(ct.expiry_date, %s) as days_until_expiry
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.status = 'Active'
            AND ct.expiry_date IS NOT NULL
            AND ct.expiry_date > %s
            AND ct.expiry_date <= %s
            ORDER BY ct.expiry_date ASC
        """
        
        expiring_tradelines = frappe.db.sql(expiring_query, (
            current_date,  # For DATEDIFF calculation
            current_date,  # Must be after today
            expiry_threshold_date  # Must be within 7 days
        ), as_dict=True)
        
        if not expiring_tradelines:
            print(f"No tradelines expiring within 7 days found.")
            return {"success": True, "message": f"No tradelines expiring within 7 days", "processed": 0}
        
        print(f"Found {len(expiring_tradelines)} tradelines expiring within 7 days")
        
        processed_count = 0
        email_failures = []
        
        # Group tradelines by customer email to send consolidated emails
        customer_tradelines = {}
        for tradeline in expiring_tradelines:
            recipient_email = tradeline.client_email_recipient if hasattr(tradeline, 'client_email_recipient') else tradeline.client_email
            if recipient_email:
                if recipient_email not in customer_tradelines:
                    customer_tradelines[recipient_email] = {
                        'customer_name': tradeline.client_full_name or tradeline.customer_name,
                        'tradelines': []
                    }
                customer_tradelines[recipient_email]['tradelines'].append(tradeline)
        
        # Send emails to each customer
        for client_email, customer_data in customer_tradelines.items():
            try:
                send_expiry_reminder_notification(client_email, customer_data)
                processed_count += 1
                print(f"Expiry reminder notification sent to {client_email}")
                
            except Exception as e:
                error_msg = f"Failed to send expiry reminder to {client_email}: {str(e)}"
                frappe.log_error(error_msg, "Expiry Reminder Notification Error")
                email_failures.append({"email": client_email, "error": str(e)})
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Sent expiry reminder notifications to {processed_count} customers",
            "processed": processed_count,
            "total_tradelines": len(expiring_tradelines),
            "expiry_threshold_days": 7
        }
        
        if email_failures:
            result["email_failures"] = email_failures
        
        print(f"Expiry reminder notifications completed. Sent to {processed_count} customers.")
        return result
        
    except Exception as e:
        error_msg = f"Expiry reminder notifications cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Expiry Reminder Notifications Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


def send_expiry_reminder_notification(client_email, customer_data):
    """
    Send expiry reminder notification email to client (7 days before expiry)
    """
    try:
        if not client_email:
            return
        
        customer_name = customer_data['customer_name']
        tradelines = customer_data['tradelines']
        
        # Format expiry date for display (Month DD, YYYY)
        from frappe.utils import formatdate
        
        # Build tradelines HTML using simple div-based layout
        tradelines_html = ""
        for tl in tradelines:
            bank_name = tl.bank_name or 'N/A'
            age_year = tl.age_year or 0
            credit_limit = f"{tl.credit_limit:,.0f}" if tl.credit_limit else "N/A"
            customer_name_au = tl.customer_name
            expiry_date = formatdate(tl.expiry_date, "MMMM dd, yyyy") if tl.expiry_date else "N/A"
            
            tradelines_html += f"""
                    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 15px; margin-bottom: 12px;">
                        <div style="font-weight: 600; color: #374151; font-size: 15px; margin-bottom: 8px;">
                            Tradeline(s): {age_year} {bank_name} ${credit_limit}
                        </div>
                        <div style="font-size: 14px; color: #6b7280; margin-bottom: 4px;">
                            <strong>AU:</strong> {customer_name_au}
                        </div>
                        <div style="font-size: 14px; color: #dc2626; font-weight: 600;">
                            <strong>Expiry Date:</strong> {expiry_date}
                        </div>
                    </div>"""
        
        # Prepare template parameters
        template_params = {
            "customer_name": customer_name,
            "tradelines_html": tradelines_html,
            "client_email": client_email
        }
        
        # Send email using Email Template Custom system
        send_email_template(
            template_name="Tradeline Expiry Reminder",
            recipients=[client_email],
            parameters=template_params
        )
        
        print(f"Expiry reminder notification sent to {client_email}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send expiry reminder to {client_email}: {str(e)}", "Expiry Reminder Notification Error")
        raise e


@frappe.whitelist()
def manual_check_expiry_reminders():
    """
    Manual trigger for expiry reminder notifications check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        result = check_and_send_expiry_reminders()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual expiry reminder check failed: {str(e)}")


@frappe.whitelist()
def get_expiring_soon_tradelines(days_ahead=7):
    """
    Get tradelines expiring within specified days (for monitoring/preview)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        current_date = getdate()
        expiry_threshold_date = add_days(current_date, int(days_ahead))
        
        expiring_query = """
            SELECT 
                ct.name as client_tradeline_id,
                ct.customer_name,
                ct.tradeline_name,
                ct.expiry_date,
                tb.bank_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                c.email_id as client_email,
                COALESCE(c.account_manager, c.email_id) as client_email_recipient,
                DATEDIFF(ct.expiry_date, %s) as days_until_expiry
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Active'
            AND ct.expiry_date IS NOT NULL
            AND ct.expiry_date > %s
            AND ct.expiry_date <= %s
            ORDER BY ct.expiry_date ASC
        """
        
        expiring_tradelines = frappe.db.sql(expiring_query, (
            current_date,  # For DATEDIFF calculation
            current_date,  # Must be after today
            expiry_threshold_date  # Must be within threshold
        ), as_dict=True)
        
        return {
            "success": True,
            "expiring_tradelines": expiring_tradelines,
            "total": len(expiring_tradelines),
            "current_date": str(current_date),
            "expiry_threshold_date": str(expiry_threshold_date),
            "days_ahead": int(days_ahead)
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch expiring tradelines: {str(e)}")


@frappe.whitelist()
def get_email_queue_status():
    """
    Get current email queue status (for monitoring)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Access denied. Administrator role required.")
        
        # Get email queue statistics
        total_emails = frappe.db.count("Email Queue")
        pending_emails = frappe.db.count("Email Queue", filters={"status": "Not Sent"})
        sent_emails = frappe.db.count("Email Queue", filters={"status": "Sent"})
        error_emails = frappe.db.count("Email Queue", filters={"status": "Error"})
        
        # Get recent pending emails
        recent_pending = frappe.get_all("Email Queue",
            filters={"status": "Not Sent"},
            fields=["name", "recipient", "subject", "creation", "modified", "retry"],
            order_by="creation desc",
            limit=10
        )
        
        # Get recent error emails
        recent_errors = frappe.get_all("Email Queue",
            filters={"status": "Error"},
            fields=["name", "recipient", "subject", "creation", "modified", "retry", "error"],
            order_by="modified desc",
            limit=5
        )
        
        return {
            "success": True,
            "statistics": {
                "total": total_emails,
                "pending": pending_emails,
                "sent": sent_emails,
                "error": error_emails
            },
            "recent_pending": recent_pending,
            "recent_errors": recent_errors
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch email queue status: {str(e)}")


def check_and_resend_pending_au_emails():
    """
    Cron job to check for client tradelines still in Pending AU status
    for more than 23 hours and resend AU assignment email
    Runs every hour to ensure cardholders receive notifications
    """
    try:
        print("Starting pending AU email reminder check...")
        
        # Calculate threshold time (23 hours ago)
        from datetime import timedelta
        threshold_time = now_datetime() - timedelta(hours=23)
        
        print(f"Checking for tradelines in Pending AU status since before {threshold_time}")
        
        # Find all client tradelines in Pending AU status for more than 23 hours
        pending_au_query = """
            SELECT 
                ct.name,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.created_date,
                ct.creation,
                ct.modified,
                ct.status,
                t.card_holder,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                c.email_id as customer_email,
                TIMESTAMPDIFF(HOUR, COALESCE(ct.created_date, ct.creation), NOW()) as hours_pending
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Pending AU'
            AND COALESCE(ct.created_date, ct.creation) <= %s
            ORDER BY ct.creation ASC
        """
        
        pending_tradelines = frappe.db.sql(pending_au_query, (threshold_time,), as_dict=True)
        
        if not pending_tradelines:
            print("No pending AU tradelines found requiring email reminders.")
            return {
                "success": True,
                "message": "No pending AU tradelines requiring reminders",
                "processed": 0
            }
        
        print(f"Found {len(pending_tradelines)} tradelines in Pending AU status for more than 23 hours")
        
        processed_count = 0
        email_failures = []
        
        for tradeline in pending_tradelines:
            try:
                # Get the client tradeline document
                client_tradeline = frappe.get_doc("Client Tradelines", tradeline.name)
                
                # Send the AU assignment reminder email using the dedicated reminder template
                result = client_tradeline.send_au_assignment_reminder_email()
                
                if result:
                    # Add a comment noting this is a reminder
                    client_tradeline.add_comment(
                        "Info",
                        f"AU assignment reminder email sent to cardholder {tradeline.cardholder_email} "
                        f"(tradeline pending for {tradeline.hours_pending} hours)"
                    )
                    processed_count += 1
                    print(f"Reminder email sent for Client Tradeline {tradeline.name} (pending {tradeline.hours_pending} hours)")
                else:
                    email_failures.append({
                        "client_tradeline": tradeline.name,
                        "cardholder_email": tradeline.cardholder_email,
                        "hours_pending": tradeline.hours_pending,
                        "error": "Email sending returned False"
                    })
                    
            except Exception as e:
                error_msg = f"Failed to send reminder for {tradeline.name}: {str(e)}"
                print(error_msg)
                email_failures.append({
                    "client_tradeline": tradeline.name,
                    "cardholder_email": tradeline.cardholder_email,
                    "hours_pending": tradeline.hours_pending,
                    "error": str(e)
                })
                frappe.log_error(error_msg, "Pending AU Reminder Error")
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Sent {processed_count} AU assignment reminder emails",
            "processed": processed_count,
            "total_found": len(pending_tradelines)
        }
        
        if email_failures:
            result["email_failures"] = email_failures
            result["failed_count"] = len(email_failures)
        
        print(f"Pending AU reminder check completed. Sent {processed_count} reminders, {len(email_failures)} failures.")
        return result
        
    except Exception as e:
        error_msg = f"Pending AU reminder cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Pending AU Reminder Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def manual_check_pending_au_reminders():
    """
    Manual trigger for pending AU reminder check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Permission Denied. Only Administrators and System Managers can trigger this task.")
        
        result = check_and_resend_pending_au_emails()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual pending AU reminder check failed: {str(e)}")


@frappe.whitelist()
def get_pending_au_tradelines(hours_threshold=23):
    """
    Get client tradelines currently in Pending AU status for more than specified hours
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Permission Denied. Only Administrators and System Managers can access this.")
        
        from datetime import timedelta
        threshold_time = now_datetime() - timedelta(hours=int(hours_threshold))
        
        pending_au_query = """
            SELECT 
                ct.name,
                ct.customer_name,
                ct.tradeline_name,
                ct.created_date,
                ct.creation,
                ct.modified,
                ct.status,
                ch.customer_name as cardholder_name,
                ch.email_id as cardholder_email,
                c.email_id as customer_email,
                TIMESTAMPDIFF(HOUR, COALESCE(ct.created_date, ct.creation), NOW()) as hours_pending,
                TIMESTAMPDIFF(MINUTE, COALESCE(ct.created_date, ct.creation), NOW()) as minutes_pending
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.status = 'Pending AU'
            AND COALESCE(ct.created_date, ct.creation) <= %s
            ORDER BY ct.creation ASC
        """
        
        pending_tradelines = frappe.db.sql(pending_au_query, (threshold_time,), as_dict=True)
        
        return {
            "success": True,
            "pending_tradelines": pending_tradelines,
            "total": len(pending_tradelines),
            "hours_threshold": int(hours_threshold)
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch pending AU tradelines: {str(e)}")


def check_and_send_removal_confirmations():
    """
    Cron job to check for client tradelines that expired in the last 24 hours
    and send removal confirmation notifications to customers (authorized users)
    Runs daily to ensure customers receive confirmation of their removal from tradelines
    """
    try:
        print("Starting removal confirmation notifications check...")
        
        # Get yesterday's date (tradelines that expired yesterday)
        yesterday = add_days(getdate(), -1)
        
        print(f"Checking for tradelines that expired on {yesterday}")
        
        # Find all client tradelines that expired yesterday
        expired_query = """
            SELECT 
                ct.name as client_tradeline_id,
                ct.customer,
                ct.customer_name,
                ct.tradeline,
                ct.tradeline_name,
                ct.expiry_date,
                ct.total_amount,
                ct.quantity,
                ct.completion_date,
                ct.is_external,
                t.name as tradeline_id,
                t.bank,
                tb.bank_name,
                t.card_holder,
                c.email_id as customer_email,
                COALESCE(c.account_manager, c.email_id) as customer_email_recipient,
                c.customer_name as customer_full_name,
                ch.email_id as cardholder_email,
                ch.customer_name as cardholder_name,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                t.price as tradeline_price
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            WHERE ct.expiry_date = %s
            AND (ct.is_external IS NULL OR ct.is_external = 0)
            ORDER BY ct.customer ASC
        """
        
        expired_tradelines = frappe.db.sql(expired_query, (yesterday,), as_dict=True)
        
        if not expired_tradelines:
            print(f"No tradelines expired on {yesterday}.")
            return {
                "success": True,
                "message": f"No tradelines expired on {yesterday}",
                "processed": 0
            }
        
        print(f"Found {len(expired_tradelines)} tradelines that expired on {yesterday}")
        
        processed_count = 0
        email_failures = []
        
        for tradeline in expired_tradelines:
            try:
                # Skip if no customer email
                if not tradeline.customer_email_recipient:
                    print(f"Warning: No email found for customer {tradeline.customer} - skipping")
                    continue
                
                # Send removal confirmation notification to customer (authorized user)
                send_removal_confirmation_notification(tradeline)
                processed_count += 1
                print(f"Removal confirmation sent to {tradeline.customer_email_recipient} for tradeline {tradeline.client_tradeline_id}")
                
            except Exception as e:
                error_msg = f"Failed to send removal confirmation for {tradeline.client_tradeline_id}: {str(e)}"
                frappe.log_error(error_msg, "Removal Confirmation Notification Error")
                email_failures.append({"tradeline": tradeline.client_tradeline_id, "error": str(e)})
        
        # Commit all changes
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": f"Sent removal confirmation notifications for {processed_count} tradelines",
            "processed": processed_count,
            "total_found": len(expired_tradelines),
            "expiry_date": str(yesterday)
        }
        
        if email_failures:
            result["email_failures"] = email_failures
        
        print(f"Removal confirmation notifications completed. Sent {processed_count} notifications.")
        return result
        
    except Exception as e:
        error_msg = f"Removal confirmation notifications cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Removal Confirmation Notifications Cron Job Error")
        print(error_msg)
        return {"success": False, "error": str(e)}


def send_removal_confirmation_notification(tradeline):
    """
    Send removal confirmation notification email to customer (authorized user)
    """
    try:
        if not tradeline.customer_email_recipient:
            return
        
        # Format credit limit
        credit_limit_formatted = f"${float(tradeline.credit_limit or 0):,.0f}" if tradeline.credit_limit else "$0"
        
        # Prepare template parameters
        template_params = {
            "customer_name": tradeline.customer_full_name or tradeline.customer_name or "Customer",
            "authorized_user_name": tradeline.customer_full_name or tradeline.customer_name or "Customer",
            "full_name": tradeline.customer_full_name or tradeline.customer_name or "Customer",
            "bank_name": tradeline.bank_name or tradeline.bank or "N/A",
            "year_opened": str(tradeline.age_year or 0),
            "credit_limit": credit_limit_formatted,
            "tradeline_description": f"{tradeline.bank_name or tradeline.bank or 'N/A'} {tradeline.age_year or 0} {credit_limit_formatted}"
        }
        
        # Send email using Email Template Custom system
        send_email_template(
            template_name="Removal Confirmation Notification",
            recipients=[tradeline.customer_email_recipient],
            parameters=template_params
        )
        
        print(f"Removal confirmation notification sent to {tradeline.customer_email_recipient}")
        
    except Exception as e:
        frappe.log_error(
            f"Failed to send removal confirmation notification to {tradeline.customer_email_recipient}: {str(e)}", 
            "Removal Confirmation Notification Error"
        )
        raise e


@frappe.whitelist()
def manual_check_removal_confirmations():
    """
    Manual trigger for removal confirmation notifications check (for testing/admin use)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Permission Denied. Only Administrators and System Managers can trigger this task.")
        
        result = check_and_send_removal_confirmations()
        return result
        
    except Exception as e:
        frappe.throw(f"Manual removal confirmation check failed: {str(e)}")


@frappe.whitelist()
def get_recently_removed_tradelines(days_back=1):
    """
    Get client tradelines that expired within specified days (for removal confirmation monitoring)
    """
    try:
        current_user = frappe.session.user
        if current_user != "Administrator" and "System Manager" not in frappe.get_roles(current_user):
            frappe.throw("Permission Denied. Only Administrators and System Managers can access this.")
        
        target_date = add_days(getdate(), -int(days_back))
        
        expired_query = """
            SELECT 
                ct.name,
                ct.customer_name,
                ct.tradeline_name,
                ct.expiry_date,
                ct.status,
                c.email_id as customer_email,
                COALESCE(c.account_manager, c.email_id) as email_recipient,
                DATE(ct.expiry_date) as expiry_date_formatted,
                DATEDIFF(CURDATE(), DATE(ct.expiry_date)) as days_since_expiry
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabCustomer` c ON ct.customer = c.name
            WHERE ct.expiry_date >= %s
            AND ct.expiry_date IS NOT NULL
            AND (ct.is_external IS NULL OR ct.is_external = 0)
            ORDER BY ct.expiry_date DESC
        """
        
        expired_tradelines = frappe.db.sql(expired_query, (target_date,), as_dict=True)
        
        return {
            "success": True,
            "expired_tradelines": expired_tradelines,
            "total": len(expired_tradelines),
            "days_back": int(days_back),
            "target_date": str(target_date)
        }
        
    except Exception as e:
        frappe.throw(f"Failed to fetch recently expired tradelines: {str(e)}")