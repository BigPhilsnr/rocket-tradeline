# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, getdate, add_days
from rockettradeline.api.auth import get_email_header, get_email_footer
from frappe.email.queue import flush
from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template


def check_and_expire_client_tradelines():
    """
    Cron job to check for expired client tradelines and send notifications
    Runs every hour to check for expired tradelines
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
                
                # Send notification to cardholder (card holder)
                if tradeline.cardholder_email:
                    send_cardholder_removal_notification(tradeline)
                else:
                    print(f"Warning: No cardholder email found for tradeline {tradeline.name}")
                
                # Send expiration notification to client
                if tradeline.client_email:
                    send_client_expiration_notification(tradeline)
                else:
                    print(f"Warning: No client email found for tradeline {tradeline.name}")
                
                processed_count += 1
                print(f"Processed expired tradeline: {tradeline.name}")
                
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
        
        # Calculate days overdue
        days_overdue = (getdate() - getdate(tradeline.expiry_date)).days
        
        # Prepare template parameters
        template_params = {
            "cardholder_name": tradeline.cardholder_name or 'Card Holder',
            "customer_name": tradeline.customer_name,
            "client_email": tradeline.client_email,
            "tradeline_id": tradeline.name,
            "expiry_date": tradeline.expiry_date,
            "days_overdue": days_overdue,
            "bank_name": tradeline.bank_name or 'N/A',
            "credit_limit": f"{tradeline.credit_limit:,.0f}" if tradeline.credit_limit else "N/A",
            "age_year": tradeline.age_year or 0,
            "age_month": tradeline.age_month or 0,
            "closing_date": tradeline.closing_date or 'N/A',
            "quantity": tradeline.quantity or 1,
            "total_amount": f"{tradeline.total_amount:,.2f}" if tradeline.total_amount else "0.00"
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
        if not tradeline.client_email:
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
            recipients=[tradeline.client_email],
            parameters=template_params
        )
        
        print(f"Client expiration notification sent to {tradeline.client_email} for tradeline {tradeline.name}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send client expiration notification: {str(e)}", "Client Notification Error")


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