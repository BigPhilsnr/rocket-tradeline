"""
RocketTradeline Feedback API
Handles feedback form submissions and management
"""

import frappe
import re
from frappe import _
from frappe.utils import cstr, now_datetime, get_datetime, now, validate_email_address
from rockettradeline.api.auth import jwt_required, get_authenticated_user

@frappe.whitelist(allow_guest=True)
@jwt_required()
def submit_feedback(question_1_why_buying, question_2_importance, question_3_credit_score, 
                   question_4_derogatory_marks, first_name, last_name, email, phone=None, source=None):
    """
    Submit tradeline feedback form
    Requires JWT authentication
    
    Args:
        question_1_why_buying (str): Reason for buying tradeline
        question_2_importance (str): Main reasons for purchasing tradeline
        question_3_credit_score (str): Current credit score range
        question_4_derogatory_marks (str): Derogatory marks on credit
        first_name (str): First name
        last_name (str): Last name
        email (str): Email address
        phone (str, optional): Phone number
        source (str, optional): Traffic source
    
    Returns:
        dict: Success message with feedback ID
    """
    try:
        # Get current authenticated user
        current_user = get_authenticated_user()
        if not current_user:
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Validate required fields
        required_fields = {
            'question_1_why_buying': question_1_why_buying,
            'question_2_importance': question_2_importance,
            'question_3_credit_score': question_3_credit_score,
            'question_4_derogatory_marks': question_4_derogatory_marks,
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value or not str(field_value).strip():
                return {
                    "success": False,
                    "message": f"Please provide {field_name.replace('_', ' ').title()}"
                }
        
        # Validate email
        try:
            validate_email_address(email.strip())
        except:
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        # Validate phone number if provided
        if phone:
            phone = phone.strip()
            # Basic phone validation (optional, can be enhanced)
            if not re.match(r'^[\+]?[\d\s\-\(\)]{10,}$', phone):
                return {
                    "success": False,
                    "message": "Please provide a valid phone number"
                }
        
        # Validate question options
        valid_options = {
            'question_1_why_buying': [
                "I want to buy a home or property",
                "I want to refinance a mortgage", 
                "I want to buy a car",
                "I want to apply for a personal or business loan",
                "Other reasons (e.g. rent a house)"
            ],
            'question_2_importance': [
                "To access lower interest rates",
                "To access higher credit limits",
                "To boost your credit score",
                "Qualify to buy a house",
                "Qualify to buy a Car"
            ],
            'question_3_credit_score': [
                "Bad credit: 300 to 579",
                "Fair credit: 630 to 689",
                "Good credit: 690 to 719",
                "Excellent credit: 720 to 850"
            ],
            'question_4_derogatory_marks': [
                "​​Late payments that are around 30 days or more past due",
                "Charge-offs",
                "Foreclosures",
                "Bankruptcy filings",
                "Repossessions"
            ]
        }
        
        for field_name, field_value in [
            ('question_1_why_buying', question_1_why_buying),
            ('question_2_importance', question_2_importance),
            ('question_3_credit_score', question_3_credit_score),
            ('question_4_derogatory_marks', question_4_derogatory_marks)
        ]:
            if field_value not in valid_options[field_name]:
                return {
                    "success": False,
                    "message": f"Invalid option for {field_name.replace('_', ' ').title()}"
                }
        
        # Get client information
        request = frappe.local.request
        ip_address = frappe.utils.get_host_name_from_request()
        user_agent = request.headers.get('User-Agent', '') if request else ''
        
        # Create feedback document
        feedback_doc = frappe.get_doc({
            "doctype": "Tradeline Feedback",
            "question_1_why_buying": question_1_why_buying.strip(),
            "question_2_importance": question_2_importance.strip(),
            "question_3_credit_score": question_3_credit_score.strip(),
            "question_4_derogatory_marks": question_4_derogatory_marks.strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip().lower(),
            "phone": phone.strip() if phone else None,
            "submission_date": now(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "source": source.strip() if source else "Website Form",
            "submitted_by_user": current_user,
            "status": "New"
        })
        
        # Add authenticated submission flag
        feedback_doc.flags.authenticated_submission = True
        
        feedback_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Update customer questionnaire status
        try:
            # Find customer by email or user
            customer = None
            
            # First try to find by email
            customers = frappe.get_all("Customer", filters={"email_id": email.strip().lower()}, fields=["name"])
            if customers:
                customer = frappe.get_doc("Customer", customers[0].name)
            else:
                # Try to find by user if authenticated
                if current_user and current_user != "Guest":
                    customers = frappe.get_all("Customer", filters={"user": current_user}, fields=["name"])
                    if customers:
                        customer = frappe.get_doc("Customer", customers[0].name)
            
            # Update questionnaire status if customer found
            if customer:
                customer.is_questionnaire_filled = 1
                customer.questionnaire_filled_date = now()
                customer.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.logger().info(f"Updated customer {customer.name} questionnaire status to filled")
            else:
                frappe.logger().info(f"No customer found for email {email} or user {current_user}")
                
        except Exception as e:
            frappe.logger().error(f"Failed to update customer questionnaire status: {str(e)}")
            # Don't fail the feedback submission if customer update fails
        
        return {
            "success": True,
            "message": "Thank you for your feedback! We'll be in touch soon.",
            "feedback_id": feedback_doc.feedback_id,
            "submission_id": feedback_doc.name,
            "submission_date": feedback_doc.submission_date,
            "authenticated": True,
            "user": current_user
        }
        
    except Exception as e:
        frappe.logger().error(f"Feedback submission error: {str(e)}")
        return {
            "success": False,
            "message": "There was an error submitting your feedback. Please try again."
        }

@frappe.whitelist()
@jwt_required()
def get_feedback_submissions(limit=50, start=0, status=None, search=None):
    """
    Get feedback submissions (Admin only)
    
    Args:
        limit (int): Number of records to return
        start (int): Starting offset
        status (str): Filter by status
        search (str): Search term for name/email
    
    Returns:
        dict: List of feedback submissions
    """
    try:
        # Check permissions
        if not frappe.has_permission("Tradeline Feedback", "read"):
            return {
                "success": False,
                "message": "Insufficient permissions to view feedback submissions"
            }
        
        # Build filters
        filters = {}
        if status:
            filters['status'] = status
        
        # Build search conditions
        conditions = ""
        if search:
            search = f"%{search}%"
            conditions = """
                AND (
                    first_name LIKE %(search)s OR 
                    last_name LIKE %(search)s OR 
                    email LIKE %(search)s OR
                    name LIKE %(search)s
                )
            """
        
        # Get submissions
        submissions = frappe.db.sql(f"""
            SELECT 
                name, feedback_id, first_name, last_name, email, phone,
                question_1_why_buying, question_2_importance, question_3_credit_score, question_4_derogatory_marks,
                submission_date, status, source, submitted_by_user, ip_address
            FROM `tabTradeline Feedback`
            WHERE 1=1 {conditions}
            ORDER BY submission_date DESC
            LIMIT %(start)s, %(limit)s
        """, {
            'start': start,
            'limit': limit,
            'search': search
        }, as_dict=True)
        
        # Get total count
        total_count = frappe.db.sql(f"""
            SELECT COUNT(*) as count
            FROM `tabTradeline Feedback`
            WHERE 1=1 {conditions}
        """, {'search': search}, as_dict=True)[0]['count']
        
        return {
            "success": True,
            "submissions": submissions,
            "total_count": total_count,
            "limit": limit,
            "start": start
        }
        
    except Exception as e:
        frappe.logger().error(f"Get feedback submissions error: {str(e)}")
        return {
            "success": False,
            "message": "Error retrieving feedback submissions"
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_feedback_details(feedback_id):
    """
    Get detailed feedback submission
    
    Args:
        feedback_id (str): Feedback ID or document name
    
    Returns:
        dict: Detailed feedback information
    """
    try:
        # Check permissions
        if not frappe.has_permission("Tradeline Feedback", "read"):
            return {
                "success": False,
                "message": "Insufficient permissions to view feedback details"
            }
        
        # Get feedback document
        filters = {}
        if feedback_id.startswith('TLF-'):
            filters['name'] = feedback_id
        else:
            filters['feedback_id'] = feedback_id
        
        feedback = frappe.get_doc("Tradeline Feedback", filters)
        
        if not feedback:
            return {
                "success": False,
                "message": "Feedback submission not found"
            }
        
        return {
            "success": True,
            "feedback": {
                "name": feedback.name,
                "feedback_id": feedback.feedback_id,
                "first_name": feedback.first_name,
                "last_name": feedback.last_name,
                "email": feedback.email,
                "phone": feedback.phone,
                "question_1_why_buying": feedback.question_1_why_buying,
                "question_2_importance": feedback.question_2_importance,
                "question_3_credit_score": feedback.question_3_credit_score,
                "question_4_derogatory_marks": feedback.question_4_derogatory_marks,
                "submission_date": feedback.submission_date,
                "status": feedback.status,
                "source": feedback.source,
                "submitted_by_user": feedback.submitted_by_user,
                "ip_address": feedback.ip_address,
                "user_agent": feedback.user_agent,
                "creation": feedback.creation,
                "modified": feedback.modified
            }
        }
        
    except Exception as e:
        frappe.logger().error(f"Get feedback details error: {str(e)}")
        return {
            "success": False,
            "message": "Error retrieving feedback details"
        }

@frappe.whitelist()
@jwt_required()
def update_feedback_status(feedback_id, status, notes=None):
    """
    Update feedback submission status
    
    Args:
        feedback_id (str): Feedback ID or document name
        status (str): New status
        notes (str): Optional notes
    
    Returns:
        dict: Success message
    """
    try:
        # Check permissions
        if not frappe.has_permission("Tradeline Feedback", "write"):
            return {
                "success": False,
                "message": "Insufficient permissions to update feedback"
            }
        
        valid_statuses = ["New", "Contacted", "Converted", "Closed"]
        if status not in valid_statuses:
            return {
                "success": False,
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }
        
        # Get feedback document
        filters = {}
        if feedback_id.startswith('TLF-'):
            filters['name'] = feedback_id
        else:
            filters['feedback_id'] = feedback_id
        
        feedback = frappe.get_doc("Tradeline Feedback", filters)
        
        if not feedback:
            return {
                "success": False,
                "message": "Feedback submission not found"
            }
        
        # Update status
        feedback.status = status
        if notes:
            # Add notes to a comment
            feedback.add_comment('Comment', text=notes)
        
        feedback.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Feedback status updated to {status}",
            "feedback_id": feedback.feedback_id,
            "new_status": status
        }
        
    except Exception as e:
        frappe.logger().error(f"Update feedback status error: {str(e)}")
        return {
            "success": False,
            "message": "Error updating feedback status"
        }

@frappe.whitelist()
@jwt_required()
def get_feedback_statistics():
    """
    Get feedback statistics and analytics
    
    Returns:
        dict: Comprehensive feedback statistics
    """
    try:
        # Check permissions
        if not frappe.has_permission("Tradeline Feedback", "read"):
            return {
                "success": False,
                "message": "Insufficient permissions to view feedback statistics"
            }
        
        # Use the static method from the doctype
        from rockettradeline.rockettradeline.doctype.tradeline_feedback.tradeline_feedback import TradelineFeedback
        stats = TradelineFeedback.get_feedback_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        frappe.logger().error(f"Get feedback statistics error: {str(e)}")
        return {
            "success": False,
            "message": "Error retrieving feedback statistics"
        }

@frappe.whitelist(allow_guest=True)
def get_feedback_form_config():
    """
    Get feedback form configuration and questions
    
    Returns:
        dict: Form configuration matching the JSON structure
    """
    return {
        "success": True,
        "form_config": {
            "questions": [
                {
                    "id": "question_1_why_buying",
                    "title": "Importance of your Credit Score",
                    "description": "Your credit score affects many key areas of life today—from determining if you qualify for a loan or credit card to influencing the interest rates you pay. It can also impact the cost of insurance premiums for your home or car, and much more.",
                    "options": [
                        {
                            "value": "I want to buy a home or property",
                            "label": "I want to buy a home or property"
                        },
                        {
                            "value": "I want to refinance a mortgage",
                            "label": "I want to refinance a mortgage"
                        },
                        {
                            "value": "I want to buy a car",
                            "label": "I want to buy a car"
                        },
                        {
                            "value": "I want to apply for a personal or business loan",
                            "label": "I want to apply for a personal or business loan"
                        },
                        {
                            "value": "other",
                            "label": "Other reasons (e.g. rent a house)"
                        }
                    ]
                },
                {
                    "id": "question_2_importance",
                    "title": "Purpose",
                    "description": "What are your main reasons for purchasing a tradeline?",
                    "options": [
                        {
                            "value": "To access lower interest rates",
                            "label": "To access lower interest rates"
                        },
                        {
                            "value": "To access higher credit limits",
                            "label": "To access higher credit limits"
                        },
                        {
                            "value": "To boost your credit score",
                            "label": "To boost your credit score"
                        },
                        {
                            "value": "Qualify to buy a house",
                            "label": "Qualify to buy a house"
                        },
                        {
                            "value": "Qualify to buy a Car",
                            "label": "Qualify to buy a Car"
                        }
                    ]
                },
                {
                    "id": "question_3_credit_score",
                    "title": "Your Credit History",
                    "description": "What is your current credit score?",
                    "options": [
                        {
                            "value": "Bad credit: 300 to 579",
                            "label": "Bad credit: 300 to 579"
                        },
                        {
                            "value": "Fair credit: 630 to 689",
                            "label": "Fair credit: 630 to 689"
                        },
                        {
                            "value": "Good credit: 690 to 719",
                            "label": "Good credit: 690 to 719"
                        },
                        {
                            "value": "Excellent credit: 720 to 850",
                            "label": "Excellent credit: 720 to 850"
                        }
                    ]
                },
                {
                    "id": "question_4_derogatory_marks",
                    "title": "Derogatory marks",
                    "description": "Do you have any of the following derogatory marks?",
                    "options": [
                        {
                            "value": "​​Late payments that are around 30 days or more past due",
                            "label": "​​Late payments that are around 30 days or more past due"
                        },
                        {
                            "value": "Charge-offs",
                            "label": "Charge-offs"
                        },
                        {
                            "value": "Foreclosures",
                            "label": "Foreclosures"
                        },
                        {
                            "value": "Bankruptcy filings",
                            "label": "Bankruptcy filings"
                        },
                        {
                            "value": "Repossessions",
                            "label": "Repossessions"
                        }
                    ]
                }
            ],
            "contact_fields": [
                {
                    "name": "first_name",
                    "label": "First Name",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "last_name",
                    "label": "Last Name",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "email",
                    "label": "Email",
                    "type": "email",
                    "required": True
                },
                {
                    "name": "phone",
                    "label": "Phone Number",
                    "type": "tel",
                    "required": False
                }
            ]
        }
    }
