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
            if not is_private and not has_administrator_role(current_user):
                return {
                    "success": False,
                    "message": "Only administrators can upload public files"
                }
            
            # Validate file_name if provided
            allowed_file_names = ['dl_front', 'dl_back', 'proof_of_address', 'client_signature']
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
            if not is_private and not has_administrator_role(current_user):
                return {
                    "success": False,
                    "message": "Only administrators can upload public files"
                }
            
            # Validate file_name if provided
            allowed_file_names = ['dl_front', 'dl_back', 'proof_of_address', 'client_signature']
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
                if not is_private and not has_administrator_role(current_user):
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

def has_administrator_role(user_name):
    """
    Check if user has Administrator role profile or is the Administrator user
    """
    try:
        if user_name == "Administrator":
            return True
            
        user_doc = frappe.get_doc("User", user_name)
        
        # Check if user has Administrator role profile
        if hasattr(user_doc, 'role_profile_name') and user_doc.role_profile_name:
            role_profile = frappe.get_doc("Role Profile", user_doc.role_profile_name)
            admin_roles = [role.role for role in role_profile.roles if role.role in ["Administrator", "System Manager"]]
            if admin_roles:
                return True
        
        # Fallback: Check individual roles
        user_roles = [role.role for role in user_doc.roles]
        return "Administrator" in user_roles or "System Manager" in user_roles
        
    except Exception:
        return False

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
    if has_administrator_role(user):
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
        if has_administrator_role(user):
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
