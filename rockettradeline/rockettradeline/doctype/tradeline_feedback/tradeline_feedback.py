import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime
import uuid

class TradelineFeedback(Document):
    def before_insert(self):
        """Set feedback ID and submission details before inserting"""
        if not self.feedback_id:
            self.feedback_id = str(uuid.uuid4())
        
        if not self.submission_date:
            self.submission_date = now()
    
    def validate(self):
        """Validate feedback data"""
        # Validate email format
        if self.email:
            frappe.utils.validate_email_address(self.email)
        
        # Ensure required fields are present
        required_fields = ['question_1_why_buying', 'question_2_importance', 'question_3_credit_score', 
                          'question_4_derogatory_marks', 'first_name', 'last_name', 'email']
        for field in required_fields:
            if not getattr(self, field):
                frappe.throw(f"Please provide {field.replace('_', ' ').title()}")
    
    def after_insert(self):
        """Post-insertion hooks"""
        # Log the feedback submission
        frappe.logger().info(f"New tradeline feedback received from {self.email} (ID: {self.feedback_id})")
        
        # Optional: Send notification to admin
        self.send_admin_notification()
        
        # Optional: Send confirmation email to user
        self.send_confirmation_email()
    
    def send_admin_notification(self):
        """Send notification to admin about new feedback"""
        try:
            # Get admin users
            admin_users = frappe.get_all("User", 
                filters={"role_profile_name": ["in", ["System Manager", "Administrator"]], "enabled": 1},
                fields=["email", "full_name"]
            )
            
            if admin_users:
                # Prepare email content
                subject = f"New Tradeline Feedback Submission - {self.name}"
                message = f"""
                <h3>New Tradeline Feedback Received</h3>
                <p><strong>Submission ID:</strong> {self.name}</p>
                <p><strong>Feedback ID:</strong> {self.feedback_id}</p>
                <p><strong>Submission Date:</strong> {self.submission_date}</p>
                
                <h4>Contact Information:</h4>
                <p><strong>Name:</strong> {self.first_name} {self.last_name}</p>
                <p><strong>Email:</strong> {self.email}</p>
                <p><strong>Phone:</strong> {self.phone or 'Not provided'}</p>
                
                <h4>Your Responses:</h4>
                <p><strong>Why buying tradeline:</strong> {self.question_1_why_buying}</p>
                <p><strong>Main reasons for purchasing:</strong> {self.question_2_importance}</p>
                <p><strong>Current credit score:</strong> {self.question_3_credit_score}</p>
                <p><strong>Derogatory marks:</strong> {self.question_4_derogatory_marks}</p>
                
                <p><a href="{frappe.utils.get_url()}/app/tradeline-feedback/{self.name}">View Full Details</a></p>
                """
                
                # Send to first admin user
                frappe.sendmail(
                    recipients=[admin_users[0]["email"]],
                    subject=subject,
                    message=message
                )
        except Exception as e:
            frappe.logger().error(f"Failed to send admin notification: {str(e)}")
    
    def send_confirmation_email(self):
        """Send confirmation email to the user"""
        try:
            subject = "Thank you for your feedback - RocketTradeline"
            message = f"""
            <h3>Thank you for your feedback!</h3>
            <p>Dear {self.first_name},</p>
            
            <p>Thank you for taking the time to share your tradeline needs with us. We have received your feedback and our team will review it shortly.</p>
            
            <h4>Your Submission Details:</h4>
            <p><strong>Submission ID:</strong> {self.name}</p>
            <p><strong>Date:</strong> {self.submission_date}</p>
            
            <h4>Your Responses:</h4>
            <p><strong>Why you're looking for a tradeline:</strong> {self.question_1_why_buying}</p>
            <p><strong>Main reasons for purchasing a tradeline:</strong> {self.question_2_importance}</p>
            <p><strong>Current credit score:</strong> {self.question_3_credit_score}</p>
            <p><strong>Derogatory marks:</strong> {self.question_4_derogatory_marks}</p>
            
            <p>Based on your responses, our team will be in touch with personalized recommendations that match your needs and timeline.</p>
            
            <p>If you have any questions, feel free to contact us at support@rockettradeline.com</p>
            
            <p>Best regards,<br>
            The RocketTradeline Team</p>
            """
            
            frappe.sendmail(
                recipients=[self.email],
                subject=subject,
                message=message
            )
        except Exception as e:
            frappe.logger().error(f"Failed to send confirmation email: {str(e)}")
    
    @staticmethod
    def get_feedback_statistics():
        """Get statistics about feedback submissions"""
        stats = {}
        
        # Total submissions
        stats['total_submissions'] = frappe.db.count('Tradeline Feedback')
        
        # Submissions by status
        stats['by_status'] = frappe.db.sql("""
            SELECT status, COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            GROUP BY status
        """, as_dict=True)
        
        # Submissions by question 1 (why buying)
        stats['by_purpose'] = frappe.db.sql("""
            SELECT question_1_why_buying, COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            GROUP BY question_1_why_buying
        """, as_dict=True)
        
        # Submissions by main reasons (question 2)
        stats['by_main_reasons'] = frappe.db.sql("""
            SELECT question_2_importance, COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            GROUP BY question_2_importance
        """, as_dict=True)
        
        # Submissions by credit score (question 3)
        stats['by_credit_score'] = frappe.db.sql("""
            SELECT question_3_credit_score, COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            GROUP BY question_3_credit_score
        """, as_dict=True)
        
        # Submissions by derogatory marks (question 4)
        stats['by_derogatory_marks'] = frappe.db.sql("""
            SELECT question_4_derogatory_marks, COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            GROUP BY question_4_derogatory_marks
        """, as_dict=True)
        
        # Recent submissions (last 7 days)
        stats['recent_submissions'] = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM `tabTradeline Feedback` 
            WHERE DATE(submission_date) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """, as_dict=True)[0]['count']
        
        return stats
