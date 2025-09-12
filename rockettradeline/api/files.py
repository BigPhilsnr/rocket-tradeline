import frappe
from frappe import _
import os
import json
import mimetypes
import base64
from frappe.utils import get_files_path, random_string, now, get_url
from frappe.utils.file_manager import save_file
from werkzeug.utils import secure_filename
import hashlib
from .auth import jwt_required, get_authenticated_user
from .utils import is_administrator
from datetime import datetime, timedelta


def get_allowed_file_names():
    """
    Get allowed file names from the Allowed File Name doctype
    Falls back to hardcoded list if doctype is not available
    """
    try:
        # Try to get from database
        file_names = frappe.get_all("Allowed File Name",
            filters={"is_active": 1},
            fields=["file_name"],
            order_by="file_name asc"
        )
        
        if file_names:
            return [item.file_name for item in file_names]
        else:
            # Fallback to hardcoded list if no records found
            return get_fallback_file_names()
            
    except Exception:
        # Fallback to hardcoded list if doctype doesn't exist or error occurs
        return get_fallback_file_names()

def get_fallback_file_names():
    """
    Fallback list of allowed file names
    """
    return [
        'dl_front', 'dl_back', 'proof_of_address', 'client_signature', 
        'proof_of_enrollment', 'proof_of_refund', 'credit_report', 
        'authorized_user_guide', 'privacy_policy', 'terms_conditions', 
        'refund_policy', 'authorized_user_agreement'
    ]
                 


# File Upload APIs

@frappe.whitelist(allow_guest=True)
@jwt_required()
def upload_file():
    """
    Upload a file to the system
    Supports both form data and base64 uploads
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        files = frappe.request.files
        form_data = frappe.local.form_dict
        
        # Check if user has permission to upload files
        if not frappe.has_permission("File", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot upload files"
            }
        
        # Handle file upload from form data
        if files and 'file' in files:
            uploaded_file = files['file']
            
            if uploaded_file.filename == '':
                return {
                    "success": False,
                    "message": "No file selected"
                }
            
            # Check if user is trying to upload public file (only admin allowed)
            is_private = int(form_data.get('is_private', 1))  # Default to private
            if not is_private and not is_administrator(current_user):
                return {
                    "success": False,
                    "message": "Only administrators can upload public files"
                }
            
            # Validate file_name if provided
            allowed_file_names = get_allowed_file_names()
            provided_file_name = form_data.get('file_name')
            if provided_file_name and provided_file_name not in allowed_file_names:
                return {
                    "success": False,
                    "message": f"Invalid file_name. Only allowed: {', '.join(allowed_file_names)}"
                }
            
            # Validate file
            validation_result = validate_file(uploaded_file)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": validation_result["message"]
                }
            
            # Generate custom filename if doctype and docname are provided
            # Get file extension from original file
            original_ext = os.path.splitext(uploaded_file.filename)[1]
            # Use file_name from form data or fallback to original filename
            base_filename = form_data.get('file_name', uploaded_file.filename)
            base_filename = secure_filename(base_filename)
            
            # Ensure the file has the correct extension
            if not base_filename.endswith(original_ext):
                name_without_ext = os.path.splitext(base_filename)[0]
                base_filename = f"{name_without_ext}{original_ext}"
            
            doctype = form_data.get('doctype')
            docname = form_data.get('docname')
            
            if doctype and docname:
                # Create custom filename: doctype_docname_filename
                custom_filename = f"{doctype}_{docname}_{base_filename}"
                custom_filename = secure_filename(custom_filename)
            else:
                custom_filename = base_filename
            
            # Save file using Frappe's file manager
            file_doc = save_file(
                fname=custom_filename,
                content=uploaded_file.read(),
                dt=doctype,
                dn=docname,
                folder=form_data.get('folder', 'Home'),
                is_private=is_private
            )
            
            # Handle proof_of_enrollment automation for Client Tradeline
            provided_file_name = form_data.get('file_name')
            if provided_file_name == 'proof_of_enrollment' and doctype == 'Client Tradelines' and docname:
                try:
                    # Get current datetime
                    completion_date = datetime.now()
                    # Calculate expiry date (61 days after completion)
                    expiry_date = completion_date + timedelta(days=61)
                    
                    # Update the Client Tradeline document
                    client_tradeline_doc = frappe.get_doc('Client Tradelines', docname)
                    client_tradeline_doc.completion_date = completion_date
                    client_tradeline_doc.expiry_date = expiry_date
                    client_tradeline_doc.save()
                    
                    frappe.db.commit()
                    
                except Exception as e:
                    frappe.log_error(f"Error updating Client Tradeline {docname}: {str(e)}", "Proof of Enrollment Automation")
            
            # Handle proof_of_refund automation for Client Tradeline
            if provided_file_name == 'proof_of_refund' and doctype == 'Client Tradelines' and docname:
                try:
                    # Get the Client Tradeline document
                    client_tradeline_doc = frappe.get_doc('Client Tradelines', docname)
                    
                    # Set status to Refunded
                    client_tradeline_doc.status = "Refunded"
                    client_tradeline_doc.save()
                    
                    # Update associated Payment Request status
                    if client_tradeline_doc.payment_request:
                        payment_request_doc = frappe.get_doc('Payment Request', client_tradeline_doc.payment_request)
                        payment_request_doc.status = "Refunded"
                        payment_request_doc.save()
                        
                        frappe.logger().info(f"Payment Request {client_tradeline_doc.payment_request} status updated to Refunded")
                    
                    frappe.db.commit()
                    frappe.logger().info(f"Proof of refund processed for Client Tradeline {docname}: status set to Refunded")
                    
                except Exception as e:
                    frappe.log_error(f"Error processing proof_of_refund for Client Tradeline {docname}: {str(e)}", "Proof of Refund Automation")
            
            return {
                "success": True,
                "message": "File uploaded successfully",
                "file": {
                    "name": file_doc.name,
                    "file_name": file_doc.file_name,
                    "file_url": file_doc.file_url,
                    "file_size": file_doc.file_size,
                    "is_private": file_doc.is_private,
                    "content_hash": file_doc.content_hash
                }
            }
        
        # Handle base64 upload
        elif form_data.get('file_content') and form_data.get('filename'):
            file_content = form_data.get('file_content')
            filename = secure_filename(form_data.get('filename'))
            
            # Check if user is trying to upload public file (only admin allowed)
            is_private = int(form_data.get('is_private', 1))  # Default to private
            if not is_private and not is_administrator(current_user):
                return {
                    "success": False,
                    "message": "Only administrators can upload public files"
                }
            
            # Validate file_name if provided
            allowed_file_names = get_allowed_file_names()
            provided_file_name = form_data.get('file_name')
            if provided_file_name and provided_file_name not in allowed_file_names:
                return {
                    "success": False,
                    "message": f"Invalid file_name. Only allowed: {', '.join(allowed_file_names)}"
                }
            
            # Decode base64 content
            try:
                if ',' in file_content:  # Handle data URL format
                    file_content = file_content.split(',')[1]
                content = base64.b64decode(file_content)
            except Exception as e:
                return {
                    "success": False,
                    "message": "Invalid base64 content"
                }
            
            # Validate content size
            if len(content) > get_max_file_size():
                return {
                    "success": False,
                    "message": f"File size exceeds maximum limit of {get_max_file_size() / (1024*1024):.1f} MB"
                }
            
            # Generate custom filename if doctype and docname are provided
            # Get file extension from original filename
            original_ext = os.path.splitext(form_data.get('filename', ''))[1]
            # Use file_name from form data or fallback to filename
            base_filename = form_data.get('file_name', form_data.get('filename', ''))
            base_filename = secure_filename(base_filename)
            
            # Ensure the file has the correct extension
            if original_ext and not base_filename.endswith(original_ext):
                name_without_ext = os.path.splitext(base_filename)[0]
                base_filename = f"{name_without_ext}{original_ext}"
            
            doctype = form_data.get('doctype')
            docname = form_data.get('docname')
            
            if doctype and docname:
                # Create custom filename: doctype_docname_filename
                custom_filename = f"{doctype}_{docname}_{base_filename}"
                custom_filename = secure_filename(custom_filename)
            else:
                custom_filename = base_filename
            
            # Save file
            file_doc = save_file(
                fname=custom_filename,
                content=content,
                dt=doctype,
                dn=docname,
                folder=form_data.get('folder', 'Home'),
                is_private=is_private
            )
            
            if provided_file_name == 'client_signature':
                frappe.db.sql("update `tabCustomer` set is_questionnaire_filled = %s where email_id = %s", (1, current_user))

            # Handle proof_of_enrollment automation for Client Tradeline
            if provided_file_name == 'proof_of_enrollment' and doctype == 'Client Tradelines' and docname:
                try:
                    # Get current datetime
                    completion_date = datetime.now()
                    # Calculate expiry date (61 days after completion)
                    expiry_date = completion_date + timedelta(days=61)
                    
                    # Update the Client Tradeline document
                    client_tradeline_doc = frappe.get_doc('Client Tradelines', docname)
                    client_tradeline_doc.completion_date = completion_date
                    client_tradeline_doc.expiry_date = expiry_date
                    client_tradeline_doc.save()
                    
                    frappe.db.commit()
                    
                except Exception as e:
                    frappe.log_error(f"Error updating Client Tradeline {docname}: {str(e)}", "Proof of Enrollment Automation")
            
            # Handle proof_of_refund automation for Client Tradeline
            if provided_file_name == 'proof_of_refund' and doctype == 'Client Tradelines' and docname:
                try:
                    # Get the Client Tradeline document
                    client_tradeline_doc = frappe.get_doc('Client Tradelines', docname)
                    
                    # Set status to Refunded
                    client_tradeline_doc.status = "Refunded"
                    client_tradeline_doc.save()
                    
                    # Update associated Payment Request status
                    if client_tradeline_doc.payment_request:
                        payment_request_doc = frappe.get_doc('Payment Request', client_tradeline_doc.payment_request)
                        payment_request_doc.status = "Refunded"
                        payment_request_doc.save()
                        
                        frappe.logger().info(f"Payment Request {client_tradeline_doc.payment_request} status updated to Refunded")
                    
                    frappe.db.commit()
                    frappe.logger().info(f"Proof of refund processed for Client Tradeline {docname}: status set to Refunded")
                    
                except Exception as e:
                    frappe.log_error(f"Error processing proof_of_refund for Client Tradeline {docname}: {str(e)}", "Proof of Refund Automation")


            return {
                "success": True,
                "message": "File uploaded successfully",
                "file": {
                    "name": file_doc.name,
                    "file_name": file_doc.file_name,
                    "file_url": file_doc.file_url,
                    "file_size": file_doc.file_size,
                    "is_private": file_doc.is_private,
                    "content_hash": file_doc.content_hash
                }
            }
        
        else:
            return {
                "success": False,
                "message": "No file provided. Use 'file' in form data or 'file_content' + 'filename' parameters"
            }
            
    except Exception as e:
        frappe.logger().error(f"File upload error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Failed to upload file: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def upload_multiple_files():
    """
    Upload multiple files at once
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        files = frappe.request.files
        form_data = frappe.local.form_dict

        user = frappe.session.user
        if not user or not frappe.has_permission("File", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot upload files"
            }

        if not files:
            return {
                "success": False,
                "message": "No files provided"
            }

        uploaded_files = []
        errors = []

        for field_name, uploaded_file in files.items():
            if uploaded_file.filename == '':
                continue

            try:
                # Validate file_name if provided
                allowed_file_names = ['dl_front', 'dl_back', 'proof_of_address']
                provided_file_name = form_data.get('file_name')
                if provided_file_name and provided_file_name not in allowed_file_names:
                    errors.append({
                        "filename": uploaded_file.filename,
                        "error": f"Invalid file_name. Only allowed: {', '.join(allowed_file_names)}"
                    })
                    continue
                
                # Check if user is trying to upload public file (only admin allowed)
                is_private = int(form_data.get('is_private', 1))  # Default to private
                if not is_private and not is_administrator(current_user):
                    errors.append({
                        "filename": uploaded_file.filename,
                        "error": "Only administrators can upload public files"
                    })
                    continue
                
                # Validate file
                validation_result = validate_file(uploaded_file)
                if not validation_result["valid"]:
                    errors.append({
                        "filename": uploaded_file.filename,
                        "error": validation_result["message"]
                    })
                    continue

                # Generate custom filename if doctype and docname are provided
                # Get file extension from original file
                original_ext = os.path.splitext(uploaded_file.filename)[1]
                # Use file_name from form data or fallback to original filename
                base_filename = form_data.get('file_name', uploaded_file.filename)
                base_filename = secure_filename(base_filename)
                
                # Ensure the file has the correct extension
                if not base_filename.endswith(original_ext):
                    name_without_ext = os.path.splitext(base_filename)[0]
                    base_filename = f"{name_without_ext}{original_ext}"
                
                doctype = form_data.get('doctype')
                docname = form_data.get('docname')
                
                if doctype and docname:
                    # Create custom filename: doctype_docname_filename
                    custom_filename = f"{doctype}_{docname}_{base_filename}"
                    custom_filename = secure_filename(custom_filename)
                else:
                    custom_filename = base_filename

                file_doc = save_file(
                    fname=custom_filename,
                    content=uploaded_file.read(),
                    dt=doctype,
                    dn=docname,
                    folder=form_data.get('folder', 'Home'),
                    is_private=is_private
                )

                uploaded_files.append({
                    "name": file_doc.name,
                    "file_name": file_doc.file_name,
                    "file_url": file_doc.file_url,
                    "file_size": file_doc.file_size,
                    "is_private": file_doc.is_private
                })

            except Exception as e:
                errors.append({
                    "filename": getattr(uploaded_file, 'filename', 'unknown'),
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"Uploaded {len(uploaded_files)} files successfully",
            "uploaded_files": uploaded_files,
            "errors": errors
        }

    except Exception as e:
        frappe.logger().error(f"Multiple file upload error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Failed to upload files: {str(e)}"
        }

# File Access APIs

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_file_info(file_name):
    """
    Get file information by file_name (not document name)
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        # Find file by file_name field, not by document name
        file_docs = frappe.get_all("File", 
            filters={"file_name": file_name},
            fields=["name"],
            limit=1
        )
        
        if not file_docs:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "File not found"
            }
        
        # Get the full document using the document name
        file_doc = frappe.get_doc("File", file_docs[0].name)
        
        # Check permissions for private files
        if file_doc.is_private and not has_file_access(file_doc):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied to private file"
            }
        
        return {
            "success": True,
            "file": {
                "name": file_doc.name,
                "file_name": file_doc.file_name,
                "file_url": file_doc.file_url,
                "file_size": file_doc.file_size,
                "file_type": file_doc.file_type,
                "is_private": file_doc.is_private,
                "folder": file_doc.folder,
                "attached_to_doctype": file_doc.attached_to_doctype,
                "attached_to_name": file_doc.attached_to_name,
                "creation": file_doc.creation,
                "modified": file_doc.modified,
                "owner": file_doc.owner
            }
        }
        
    except frappe.DoesNotExistError:
        frappe.local.response.http_status_code = 404
        return {
            "success": False,
            "message": "File not found"
        }
    except Exception as e:
        frappe.logger().error(f"Get file info error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def download_file(file_name=None):
    """
    Download file by file_name (not document name)
    Supports both GET (query parameter) and POST (JSON body) requests
    """
    try:
        # Initialize response object early
        if not hasattr(frappe.local, 'response') or frappe.local.response is None:
            frappe.local.response = frappe._dict()
        if not hasattr(frappe.local.response, 'headers') or frappe.local.response.headers is None:
            frappe.local.response.headers = frappe._dict()
            
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Get file_name from either query parameter (GET) or JSON body (POST)
        if not file_name:
            # Try to get from form_dict (POST JSON body or GET query parameters)
            file_name = frappe.local.form_dict.get('file_name')
        
        if not file_name:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "file_name parameter is required"
            }
        
        # Find file by file_name field, not by document name
        file_docs = frappe.get_all("File", 
            filters={"file_name": file_name},
            fields=["name"],
            limit=1
        )
        
        if not file_docs:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "File not found"
            }
        
        # Get the full document using the document name
        file_doc = frappe.get_doc("File", file_docs[0].name)
        
        # Check permissions for private files
        if file_doc.is_private and not has_file_access(file_doc):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied to private file"
            }
        
        # Get file path
        file_path = get_files_path(file_doc.file_name, is_private=file_doc.is_private)
        
        if not os.path.exists(file_path):
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "File not found on disk"
            }
        
        # Initialize response object properly for binary data
        if not hasattr(frappe.local, 'response') or frappe.local.response is None:
            frappe.local.response = frappe._dict()
        if not hasattr(frappe.local.response, 'headers') or frappe.local.response.headers is None:
            frappe.local.response.headers = frappe._dict()
        
        # Set response headers for file download
        frappe.local.response.headers["Content-Type"] = file_doc.file_type or "application/octet-stream"
        frappe.local.response.headers["Content-Disposition"] = f'attachment; filename="{file_doc.file_name}"'
        frappe.local.response.headers["Content-Length"] = str(os.path.getsize(file_path))
        
        # Read and return file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
            
        # Set the response data
        frappe.local.response.data = file_content
        
        # Return None to indicate binary response
        return
        
    except frappe.DoesNotExistError:
        frappe.local.response.http_status_code = 404
        return {
            "success": False,
            "message": "File not found"
        }
    except Exception as e:
        frappe.logger().error(f"Download file error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_files_list(doctype=None, docname=None, folder=None, is_private=None, 
                   limit=50, start=0, search=None):
    """
    Get list of files with filtering options
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        if not frappe.has_permission("File", "read"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot read files"
            }
        
        filters = {}
        
        # Apply filters
        if doctype:
            filters["attached_to_doctype"] = doctype
        if docname:
            filters["attached_to_name"] = docname
        if folder:
            filters["folder"] = folder
        if is_private is not None:
            filters["is_private"] = int(is_private)
        if not is_administrator(current_user):
            filters["owner"] = current_user

        # Add search functionality
        if search:
            filters["file_name"] = ["like", f"%{search}%"]
        
        # Get files
        files = frappe.get_all("File",
            filters=filters,
            fields=["name", "file_name", "file_url", "file_size", "file_type",
                   "is_private", "folder", "attached_to_doctype", "attached_to_name",
                   "creation", "modified", "owner"],
            limit=limit,
            start=start,
            order_by="creation desc"
        )
        
        # Get total count for pagination
        total_count = frappe.db.count("File", filters)
        
        return {
            "success": True,
            "files": files,
            "total_count": total_count,
            "limit": limit,
            "start": start
        }
        
    except Exception as e:
        frappe.logger().error(f"Get files list error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def delete_file(file_name):
    """
    Delete file by file_name (not document name)
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        # Find file by file_name field, not by document name
        file_docs = frappe.get_all("File", 
            filters={"file_name": file_name},
            fields=["name"],
            limit=1
        )
        
        if not file_docs:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "File not found"
            }
        
        # Get the full document using the document name
        file_doc = frappe.get_doc("File", file_docs[0].name)
        
        # Check permissions
        if not frappe.has_permission("File", "delete", doc=file_doc):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot delete this file"
            }
        
        # Delete the file
        file_doc.delete()
        
        return {
            "success": True,
            "message": "File deleted successfully"
        }
        
    except frappe.DoesNotExistError:
        frappe.local.response.http_status_code = 404
        return {
            "success": False,
            "message": "File not found"
        }
    except Exception as e:
        frappe.logger().error(f"Delete file error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

# File Management Utilities

@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_folder(folder_name, parent_folder="Home"):
    """
    Create a new folder
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        if not frappe.has_permission("File", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot create folders"
            }
        
        # Check if folder already exists
        existing_folder = frappe.get_all("File",
            filters={
                "is_folder": 1,
                "file_name": folder_name,
                "folder": parent_folder
            },
            limit=1
        )
        
        if existing_folder:
            return {
                "success": False,
                "message": "Folder already exists"
            }
        
        # Create folder
        folder_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": folder_name,
            "is_folder": 1,
            "folder": parent_folder
        })
        folder_doc.insert()
        
        return {
            "success": True,
            "message": "Folder created successfully",
            "folder": {
                "name": folder_doc.name,
                "file_name": folder_doc.file_name,
                "folder": folder_doc.folder
            }
        }
        
    except Exception as e:
        frappe.logger().error(f"Create folder error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_folders():
    """
    Get list of all folders
    """
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {"success": False, "message": "Authentication required"}
        
        if not frappe.has_permission("File", "read"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied: Cannot read folders"
            }
        
        folders = frappe.get_all("File",
            filters={"is_folder": 1},
            fields=["name", "file_name", "folder", "creation", "modified"],
            order_by="folder asc, file_name asc"
        )
        
        return {
            "success": True,
            "folders": folders
        }
        
    except Exception as e:
        frappe.logger().error(f"Get folders error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_file_by_url(file_url):
    """
    Get file information by file URL
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        # Extract file name from URL
        if "/files/" in file_url:
            file_name = file_url.split("/files/")[-1]
        else:
            return {
                "success": False,
                "message": "Invalid file URL"
            }
        
        file_doc = frappe.get_all("File",
            filters={"file_url": file_url},
            fields=["name", "file_name", "file_url", "file_size", "file_type",
                   "is_private", "folder", "creation", "modified"],
            limit=1
        )
        
        if not file_doc:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "File not found"
            }
        
        file_info = file_doc[0]
        
        # Check permissions for private files
        if file_info.is_private and not has_file_access_by_url(file_url):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied to private file"
            }
        
        return {
            "success": True,
            "file": file_info
        }
        
    except Exception as e:
        frappe.logger().error(f"Get file by URL error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

# Helper Functions

def validate_file(uploaded_file):
    """
    Validate uploaded file
    """
    # Check file size
    uploaded_file.seek(0, 2)  # Seek to end
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)  # Reset to beginning
    
    max_size = get_max_file_size()
    if file_size > max_size:
        return {
            "valid": False,
            "message": f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum limit of {max_size / (1024*1024):.1f} MB"
        }
    
    # Check file extension
    allowed_extensions = get_allowed_file_extensions()
    if allowed_extensions:
        file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return {
                "valid": False,
                "message": f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            }
    
    return {"valid": True}

def get_max_file_size():
    """
    Get maximum file size from site config
    """
    return frappe.conf.get("max_file_size", 25 * 1024 * 1024)  # Default 25MB

def get_allowed_file_extensions():
    """
    Get allowed file extensions from site config
    """
    return frappe.conf.get("allowed_file_extensions", [
        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', 
        '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar'
    ])

def has_file_access(file_doc):
    """
    Check if current user has access to file
    """
    user = frappe.session.user
    if is_administrator(user):
        return True
    
    if not file_doc.is_private:
        return True
    
    # Owner can always access
    if file_doc.owner == user:
        return True
    
    # Check if user has access to the attached document
    if file_doc.attached_to_doctype and file_doc.attached_to_name:
        return frappe.has_permission(file_doc.attached_to_doctype, "read", file_doc.attached_to_name)
    
    # Check if user has file permissions
    return frappe.has_permission("File", "read", file_doc.name)

def has_file_access_by_url(file_url):
    """
    Check if current user has access to file by URL
    """
    try:
        file_doc = frappe.get_all("File",
            filters={"file_url": file_url},
            fields=["name", "is_private", "owner", "attached_to_doctype", "attached_to_name"],
            limit=1
        )
        
        if not file_doc:
            return False
        
        file_info = file_doc[0]

        user = frappe.session.user
        if is_administrator(user):
            return True

        if not file_info.is_private:
            return True

        if file_info.owner == user:
            return True

        if file_info.attached_to_doctype and file_info.attached_to_name:
            return frappe.has_permission(file_info.attached_to_doctype, "read", file_info.attached_to_name)

        return frappe.has_permission("File", "read", file_info.name)
        
    except Exception:
        return False

# Image Processing APIs (Optional)

@frappe.whitelist(allow_guest=True)
@jwt_required()
def resize_image(file_name, width=None, height=None, maintain_aspect_ratio=True):
    """
    Resize an image file by file_name (not document name)
    Requires Pillow library
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        from PIL import Image
        
        # Find file by file_name field, not by document name
        file_docs = frappe.get_all("File", 
            filters={"file_name": file_name},
            fields=["name"],
            limit=1
        )
        
        if not file_docs:
            return {
                "success": False,
                "message": "File not found"
            }
        
        # Get the full document using the document name
        file_doc = frappe.get_doc("File", file_docs[0].name)
        
        # Check if it's an image
        if not file_doc.file_type or not file_doc.file_type.startswith('image/'):
            return {
                "success": False,
                "message": "File is not an image"
            }
        
        # Check permissions
        if not has_file_access(file_doc):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied to file"
            }
        
        # Get file path
        file_path = get_files_path(file_doc.file_name, is_private=file_doc.is_private)
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": "File not found on disk"
            }
        
        # Open and resize image
        with Image.open(file_path) as img:
            original_width, original_height = img.size
            
            # Calculate new dimensions
            if width and height:
                if maintain_aspect_ratio:
                    # Calculate aspect ratio
                    aspect_ratio = original_width / original_height
                    if width / height > aspect_ratio:
                        width = int(height * aspect_ratio)
                    else:
                        height = int(width / aspect_ratio)
                new_size = (width, height)
            elif width:
                aspect_ratio = original_width / original_height
                height = int(width / aspect_ratio)
                new_size = (width, height)
            elif height:
                aspect_ratio = original_width / original_height
                width = int(height * aspect_ratio)
                new_size = (width, height)
            else:
                return {
                    "success": False,
                    "message": "Either width or height must be specified"
                }
            
            # Resize image
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save resized image as new file
            import io
            output = io.BytesIO()
            img_format = img.format or 'JPEG'
            resized_img.save(output, format=img_format)
            output.seek(0)
            
            # Create new filename
            name, ext = os.path.splitext(file_doc.file_name)
            new_filename = f"{name}_resized_{width}x{height}{ext}"
            
            # Save as new file
            new_file_doc = save_file(
                fname=new_filename,
                content=output.read(),
                dt=None,
                dn=None,
                folder=file_doc.folder,
                is_private=file_doc.is_private
            )
            
            return {
                "success": True,
                "message": "Image resized successfully",
                "original_file": {
                    "name": file_doc.name,
                    "dimensions": f"{original_width}x{original_height}"
                },
                "resized_file": {
                    "name": new_file_doc.name,
                    "file_name": new_file_doc.file_name,
                    "file_url": new_file_doc.file_url,
                    "dimensions": f"{width}x{height}"
                }
            }
            
    except ImportError:
        return {
            "success": False,
            "message": "Pillow library not installed. Cannot resize images."
        }
    except Exception as e:
        frappe.logger().error(f"Resize image error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

# Allowed File Names Management APIs

@frappe.whitelist()
@jwt_required()
def get_allowed_file_names_list():
    """
    Get list of all allowed file names with details (Admin only)
    """
    try:
        current_user = get_authenticated_user()
        if not is_administrator(current_user):
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
        
        file_names = frappe.get_all("Allowed File Name",
            fields=["name", "file_name", "description", "category", "is_active", "created_date", "modified_date"],
            order_by="category asc, file_name asc"
        )
        
        return {
            "success": True,
            "file_names": file_names,
            "total_count": len(file_names)
        }
        
    except Exception as e:
        frappe.log_error(f"Get allowed file names error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
@jwt_required()
def add_allowed_file_name(file_name, description=None, category="Other"):
    """
    Add a new allowed file name (Admin only)
    """
    try:
        current_user = get_authenticated_user()
        if not is_administrator(current_user):
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
            
        if not file_name:
            return {
                "success": False,
                "message": "File name is required"
            }
            
        # Clean the file name
        clean_name = file_name.strip().lower().replace(" ", "_")
        
        # Check if already exists
        if frappe.db.exists("Allowed File Name", clean_name):
            return {
                "success": False,
                "message": f"File name '{clean_name}' already exists"
            }
            
        # Create new document
        doc = frappe.get_doc({
            "doctype": "Allowed File Name",
            "file_name": clean_name,
            "description": description,
            "category": category,
            "is_active": 1
        })
        
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"File name '{clean_name}' added successfully",
            "file_name": clean_name
        }
        
    except Exception as e:
        frappe.log_error(f"Add allowed file name error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
@jwt_required()
def update_allowed_file_name(file_name, description=None, category=None, is_active=None):
    """
    Update an allowed file name (Admin only)
    """
    try:
        current_user = get_authenticated_user()
        if not is_administrator(current_user):
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
            
        if not file_name:
            return {
                "success": False,
                "message": "File name is required"
            }
            
        # Get the document
        if not frappe.db.exists("Allowed File Name", file_name):
            return {
                "success": False,
                "message": f"File name '{file_name}' not found"
            }
            
        doc = frappe.get_doc("Allowed File Name", file_name)
        
        # Update fields if provided
        if description is not None:
            doc.description = description
        if category is not None:
            doc.category = category
        if is_active is not None:
            doc.is_active = int(is_active)
            
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"File name '{file_name}' updated successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Update allowed file name error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
@jwt_required()
def delete_allowed_file_name(file_name):
    """
    Delete an allowed file name (Admin only)
    """
    try:
        current_user = get_authenticated_user()
        if not is_administrator(current_user):
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
            
        if not file_name:
            return {
                "success": False,
                "message": "File name is required"
            }
            
        # Check if exists
        if not frappe.db.exists("Allowed File Name", file_name):
            return {
                "success": False,
                "message": f"File name '{file_name}' not found"
            }
            
        # Delete the document
        frappe.delete_doc("Allowed File Name", file_name, ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"File name '{file_name}' deleted successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Delete allowed file name error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_allowed_file_names_public():
    """
    Get list of active allowed file names (public endpoint for frontend)
    """
    try:
        file_names = get_allowed_file_names()
        
        return {
            "success": True,
            "file_names": file_names
        }
        
    except Exception as e:
        frappe.log_error(f"Get public allowed file names error: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "file_names": get_fallback_file_names()
        }
