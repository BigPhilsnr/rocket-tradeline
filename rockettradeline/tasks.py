# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, getdate, add_days
from rockettradeline.api.auth import get_email_header, get_email_footer


def check_and_expire_client_tradelines():
    """
    Cron job to check for expired client tradelines and send notifications
    Runs every hour to check for expired tradelines
    """
    try:
        frappe.logger().info("Starting expired client tradelines check...")
        
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
            frappe.logger().info("No expired client tradelines found.")
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
                    frappe.logger().warning(f"No cardholder email found for tradeline {tradeline.name}")
                
                # Send expiration notification to client
                if tradeline.client_email:
                    send_client_expiration_notification(tradeline)
                else:
                    frappe.logger().warning(f"No client email found for tradeline {tradeline.name}")
                
                processed_count += 1
                frappe.logger().info(f"Processed expired tradeline: {tradeline.name}")
                
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
        
        frappe.logger().info(f"Expired tradelines check completed. Processed: {processed_count}")
        return result
        
    except Exception as e:
        error_msg = f"Expired tradelines cron job failed: {str(e)}"
        frappe.log_error(error_msg, "Expired Tradelines Cron Job Error")
        frappe.logger().error(error_msg)
        return {"success": False, "error": str(e)}


def send_cardholder_removal_notification(tradeline):
    """
    Send email notification to cardholder to remove the client from tradeline
    """
    try:
        if not tradeline.cardholder_email:
            return
        
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(tradeline.cardholder_email)
        
        # Prepare email content
        subject = f"Client Removal Required - {tradeline.bank_name or 'Tradeline'} Expired"
        
        message = f"""{email_header}
        <h3 style="color: #DC2626; margin: 0 0 20px 0;">Client Tradeline Expired - Removal Required</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {tradeline.cardholder_name or 'Card Holder'},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            A client's tradeline subscription has expired and requires immediate attention. Please remove the following client from your tradeline as soon as possible.
        </p>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Client Removal Details:</h4>
        <div style="background-color: #fef2f2; border-left: 4px solid #DC2626; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Client Name:</strong> {tradeline.customer_name}</p>
            <p style="margin: 5px 0;"><strong>Client Email:</strong> {tradeline.client_email}</p>
            <p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {tradeline.name}</p>
            <p style="margin: 5px 0;"><strong>Expired Date:</strong> {tradeline.expiry_date}</p>
            <p style="margin: 5px 0;"><strong>Duration:</strong> {(getdate() - getdate(tradeline.expiry_date)).days} days overdue</p>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Information:</h4>
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Bank:</strong> {tradeline.bank_name or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${tradeline.credit_limit:,}</p>
            <p style="margin: 5px 0;"><strong>Account Age:</strong> {tradeline.age_year} years {tradeline.age_month or 0} months</p>
            <p style="margin: 5px 0;"><strong>Closing Date:</strong> {tradeline.closing_date}</p>
            <p style="margin: 5px 0;"><strong>Spots Purchased:</strong> {tradeline.quantity}</p>
            <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ${tradeline.total_amount}</p>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Required Actions:</h4>
        <div style="background-color: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <ol style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                <li style="margin: 5px 0;"><strong>Remove the client</strong> as an authorized user from your credit card account</li>
                <li style="margin: 5px 0;"><strong>Update your account</strong> to reflect the removal</li>
                <li style="margin: 5px 0;"><strong>Verify removal</strong> within 3-5 business days</li>
                <li style="margin: 5px 0;"><strong>Contact support</strong> if you need assistance with the removal process</li>
            </ol>
        </div>
        
        <div style="background-color: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 25px 0;">
            <p style="margin: 0; color: #DC2626; font-weight: 600; font-size: 14px;">
                ⚠️ Important: Failure to remove expired clients promptly may affect your tradeline performance and future earnings.
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://rocket-app.tiberbuhealth.com/app" 
               style="background-color: #DC2626; color: white; padding: 12px 24px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                Access Seller Portal
            </a>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            If you have any questions about the removal process, please contact our support team immediately.
        </p>
        {email_footer}"""
        
        # Send email
        frappe.sendmail(
            recipients=[tradeline.cardholder_email],
            subject=subject,
            message=message,
            header=["Client Removal Required", "red"]
        )
        
        frappe.logger().info(f"Cardholder removal notification sent to {tradeline.cardholder_email} for tradeline {tradeline.name}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send cardholder removal notification: {str(e)}", "Cardholder Notification Error")


def send_client_expiration_notification(tradeline):
    """
    Send email notification to client about tradeline expiration
    """
    try:
        if not tradeline.client_email:
            return
        
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(tradeline.client_email)
        
        # Prepare email content
        subject = f"Tradeline Expired - {tradeline.bank_name or 'Your Tradeline'}"
        
        message = f"""{email_header}
        <h3 style="color: #F59E0B; margin: 0 0 20px 0;">Your Tradeline Has Expired</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {tradeline.customer_name},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Your tradeline subscription has reached its expiration date. Your authorized user status has been scheduled for removal from the tradeline account.
        </p>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Summary:</h4>
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {tradeline.name}</p>
            <p style="margin: 5px 0;"><strong>Bank:</strong> {tradeline.bank_name or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${tradeline.credit_limit:,}</p>
            <p style="margin: 5px 0;"><strong>Account Age:</strong> {tradeline.age_year} years {tradeline.age_month or 0} months</p>
            <p style="margin: 5px 0;"><strong>Subscription Period:</strong> {tradeline.completion_date or 'N/A'} to {tradeline.expiry_date}</p>
            <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ${tradeline.total_amount}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: #F59E0B; font-weight: bold;">Expired</span></p>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">What Happens Next:</h4>
        <div style="background-color: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                <li style="margin: 8px 0;"><strong>Removal Process:</strong> You will be removed as an authorized user within 3-5 business days</li>
                <li style="margin: 8px 0;"><strong>Credit Report Impact:</strong> The tradeline may continue to appear on your credit report for some time after removal</li>
                <li style="margin: 8px 0;"><strong>Score Changes:</strong> Your credit score may be affected once the tradeline is removed</li>
                <li style="margin: 8px 0;"><strong>New Tradelines:</strong> Browse our marketplace for additional tradeline opportunities</li>
            </ul>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Service Review:</h4>
        <div style="background-color: #f0f9ff; border-left: 4px solid #0EA5E9; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 0 0 15px 0; color: #374151;">
                We hope this tradeline helped improve your credit profile. Your feedback is valuable to us and helps improve our service.
            </p>
            <p style="margin: 0; color: #6b7280;">
                <strong>Duration:</strong> {(getdate(tradeline.expiry_date) - getdate(tradeline.completion_date or tradeline.expiry_date)).days if tradeline.completion_date else 'N/A'} days<br>
                <strong>Investment:</strong> ${tradeline.total_amount} for {tradeline.quantity} spot(s)
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <div style="margin-bottom: 15px;">
                <a href="https://rocket-app.tiberbuhealth.com/app" 
                   style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                          border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block; margin-right: 10px;">
                    Browse New Tradelines
                </a>
            </div>
            <div>
                <a href="https://rocket-app.tiberbuhealth.com/support" 
                   style="background-color: #6b7280; color: white; padding: 10px 20px; text-decoration: none; 
                          border-radius: 6px; font-weight: 500; font-size: 14px; display: inline-block;">
                    Contact Support
                </a>
            </div>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            Thank you for choosing RocketTradeline. We look forward to serving you again in the future!
        </p>
        {email_footer}"""
        
        # Send email
        frappe.sendmail(
            recipients=[tradeline.client_email],
            subject=subject,
            message=message,
            header=["Tradeline Expiration Notice", "orange"]
        )
        
        frappe.logger().info(f"Client expiration notification sent to {tradeline.client_email} for tradeline {tradeline.name}")
        
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