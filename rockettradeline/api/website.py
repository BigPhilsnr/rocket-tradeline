from rockettradeline.api.auth import jwt_required, get_current_user, require_roles
import frappe
from frappe import _
import json
from .utils import get_authenticated_user, is_administrator

# Site Content APIs

@frappe.whitelist(allow_guest=True)
def get_site_content(key=None, section=None, page=None):
    """
    Get site content by key, section, and/or page
    """
    try:
        filters = {"is_active": 1}
        
        if key:
            filters["key"] = key
        if section:
            filters["section"] = section
        if page:
            filters["page"] = page
        
        content = frappe.get_all("Site Content",
            filters=filters,
            fields=["key", "value", "section", "page", "content_type"],
            order_by="`page` asc, `section` asc, `key` asc"
        )
        
        return {
            "success": True,
            "content": content
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_content_by_key(key):
    """
    Get content value by key
    """
    try:
        content = frappe.get_all("Site Content", 
            filters={"key": key, "is_active": 1},
            fields=["value", "content_type"],
            limit=1
        )
        
        if content:
            return {
                "success": True,
                "key": key,
                "value": content[0].value,
                "content_type": content[0].content_type
            }
        else:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": f"Content with key '{key}' not found"
            }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def set_site_content(key, value, section, page, content_type="Text"):
    """
    Set site content by key, create if not exists
    Requires System Manager or Administrator role
    """
    try:
        user =  get_authenticated_user()
        if not user or not is_administrator(user):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
        
        # Check if content already exists
        existing = frappe.get_all("Site Content", 
            filters={"key": key},
            limit=1
        )
        
        if existing:
            content_doc = frappe.get_doc("Site Content", existing[0].name)
            content_doc.value = value
            content_doc.section = section
            content_doc.page = page
            content_doc.content_type = content_type
            content_doc.save(ignore_permissions=True)
            action = "updated"
        else:
            content_doc = frappe.get_doc({
                "doctype": "Site Content",
                "key": key,
                "value": value,
                "section": section,
                "page": page,
                "content_type": content_type,
                "is_active": 1
            })
            content_doc.insert(ignore_permissions=True)
            action = "created"
        
        return {
            "success": True,
            "message": f"Site content {action} successfully",
            "content": {
                "key": content_doc.key,
                "value": content_doc.value,
                "section": content_doc.section,
                "page": content_doc.page,
                "content_type": content_doc.content_type
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("System Manager", "Administrator")
def bulk_set_site_content(content_list):
    """
    Bulk set site content - accepts list of content items
    Format: [{"key": "key1", "value": "value1", "section": "section1", "page": "page1", "content_type": "Text"}, ...]
    Requires System Manager or Administrator role
    """
    try:
        user =  get_authenticated_user()
        if not user or not is_administrator(user):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
        
        if isinstance(content_list, str):
            content_list = json.loads(content_list)
        
        results = []
        errors = []
        
        for item in content_list:
            try:
                key = item.get("key")
                value = item.get("value")
                section = item.get("section")
                page = item.get("page")
                content_type = item.get("content_type", "Text")
                
                if not all([key, value, section, page]):
                    errors.append({
                        "key": key,
                        "error": "Missing required fields (key, value, section, page)"
                    })
                    continue
                
                existing = frappe.get_all("Site Content", 
                    filters={"key": key},
                    limit=1
                )
                
                if existing:
                    content_doc = frappe.get_doc("Site Content", existing[0].name)
                    content_doc.value = value
                    content_doc.section = section
                    content_doc.page = page
                    content_doc.content_type = content_type
                    content_doc.save(ignore_permissions=True)
                    action = "updated"
                else:
                    content_doc = frappe.get_doc({
                        "doctype": "Site Content",
                        "key": key,
                        "value": value,
                        "section": section,
                        "page": page,
                        "content_type": content_type,
                        "is_active": 1
                    })
                    content_doc.insert(ignore_permissions=True)
                    action = "created"
                
                results.append({
                    "key": key,
                    "action": action,
                    "success": True
                })
                
            except Exception as e:
                errors.append({
                    "key": item.get("key", "unknown"),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Processed {len(results)} items successfully, {len(errors)} errors",
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def delete_site_content(key):
    """
    Delete site content by key
    """
    user =  get_authenticated_user()
    if not user or not frappe.has_permission("Site Content", "delete"):
        frappe.local.response.http_status_code = 403
        return {
            "success": False,
            "message": "Permission denied"
        }
    existing = frappe.get_all("Site Content", 
        filters={"key": key},
        limit=1
    )
    if existing:
        frappe.delete_doc("Site Content", existing[0].name)
        return {
            "success": True,
            "message": f"Site content with key '{key}' deleted successfully"
        }
    else:
        frappe.local.response.http_status_code = 404
        return {
            "success": False,
            "message": f"Content with key '{key}' not found"
        }

# Legacy Website Settings APIs (for backward compatibility)

@frappe.whitelist(allow_guest=True)
def get_website_settings():
    """
    Get website settings (backward compatibility)
    """
    try:
        # Get all website-related content
        content = frappe.get_all("Site Content",
            filters={"section": "website", "is_active": 1},
            fields=["key", "value"],
            order_by="key asc"
        )
        
        # Convert to legacy format
        settings = {}
        for item in content:
            settings[item.key] = item.value
        
        return {
            "success": True,
            "settings": settings
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def update_website_settings(**kwargs):
    """
    Update website settings (backward compatibility)
    """
    user =  get_authenticated_user()
    if not user or not frappe.has_permission("Site Content", "write"):
        frappe.local.response.http_status_code = 403
        return {
            "success": False,
            "message": "Permission denied"
        }
    # Update each field as site content
    for field, value in kwargs.items():
        if value is not None:
            set_site_content(field, value, "website", "general", "Text")
    return {
        "success": True,
        "message": "Website settings updated successfully"
    }

# FAQ APIs

@frappe.whitelist(allow_guest=True)
def get_faqs(category=None, limit=50, start=0):
    """
    Get list of FAQs
    """
    try:
        # Convert limit and start to integers with validation
        try:
            limit = int(limit) if limit else 50
            start = int(start) if start else 0
        except (ValueError, TypeError):
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Invalid pagination parameters. 'limit' and 'start' must be valid integers."}
        
        filters = {"is_published": 1}
        
        if category:
            filters["category"] = category
        
        # Get total count for pagination
        total_count = frappe.db.count("FAQ", filters)
        
        faqs = frappe.get_all("FAQ",
            filters=filters,
            fields=["name", "question", "answer", "category", "sort_order"],
            limit=limit,
            start=start,
            order_by="sort_order asc, creation asc"
        )
        
        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0
        
        return {
            "success": True,
            "faqs": faqs,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_faq(question, answer, category=None, sort_order=0):
    """
    Create new FAQ
    """
    try:
        if not frappe.has_permission("FAQ", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        faq = frappe.get_doc({
            "doctype": "FAQ",
            "question": question,
            "answer": answer,
            "category": category,
            "sort_order": sort_order,
            "is_published": 1
        })
        
        faq.insert()
        
        return {
            "success": True,
            "message": "FAQ created successfully",
            "faq": {
                "name": faq.name,
                "question": faq.question,
                "answer": faq.answer
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_faq(faq_id, question=None, answer=None, category=None, 
               sort_order=None, is_published=None):
    """
    Update FAQ
    """
    try:
        if not frappe.has_permission("FAQ", "write"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        faq = frappe.get_doc("FAQ", faq_id)
        
        if question:
            faq.question = question
        if answer:
            faq.answer = answer
        if category:
            faq.category = category
        if sort_order is not None:
            faq.sort_order = sort_order
        if is_published is not None:
            faq.is_published = is_published
        
        faq.save()
        
        return {
            "success": True,
            "message": "FAQ updated successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def delete_faq(faq_id):
    """
    Delete FAQ
    """
    try:
        if not frappe.has_permission("FAQ", "delete"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        frappe.delete_doc("FAQ", faq_id)
        
        return {
            "success": True,
            "message": "FAQ deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def import_faqs_from_file():
    """
    Import FAQs from uploaded CSV file (simplified version without pandas dependency)
    Expected columns: question, answer, category (optional), sort_order (optional), is_published (optional)
    """
    try:
        # Check permissions
        user = get_authenticated_user()
        if not user or not is_administrator(user):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
        
        import csv
        import io
        
        # Check if file was uploaded
        if not frappe.request.files.get('file'):
            return {
                "success": False,
                "message": "No file uploaded. Please upload a CSV (.csv) file."
            }
        
        uploaded_file = frappe.request.files['file']
        filename = uploaded_file.filename.lower()
        
        # Validate file type (only CSV for now to avoid pandas dependency)
        if not filename.endswith('.csv'):
            return {
                "success": False,
                "message": "Invalid file format. Please upload CSV (.csv) file. Excel files require pandas library installation."
            }
        
        # Read CSV file content
        try:
            file_content = uploaded_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_content))
            rows = list(csv_reader)
        except UnicodeDecodeError:
            try:
                # Try with different encoding
                uploaded_file.seek(0)
                file_content = uploaded_file.read().decode('utf-8-sig')
                csv_reader = csv.DictReader(io.StringIO(file_content))
                rows = list(csv_reader)
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error reading CSV file. Please ensure it's properly formatted UTF-8 CSV: {str(e)}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading CSV file: {str(e)}"
            }
        
        if not rows:
            return {
                "success": False,
                "message": "The CSV file appears to be empty or has no data rows."
            }
        
        # Get column names from first row
        columns = list(rows[0].keys()) if rows else []
        
        # Validate required columns
        required_columns = ['question', 'answer']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            available_columns = ', '.join(columns)
            return {
                "success": False,
                "message": f"Missing required columns: {', '.join(missing_columns)}. Required columns are: question, answer. Available columns: {available_columns}"
            }
        
        # Process each row
        results = {
            "created": [],
            "updated": [],
            "errors": [],
            "skipped": []
        }
        
        total_rows = len(rows)
        
        for index, row in enumerate(rows):
            try:
                # Clean and validate data
                question = str(row.get('question', '')).strip()
                answer = str(row.get('answer', '')).strip()
                category = str(row.get('category', '')).strip() if row.get('category') else None
                
                # Remove empty category
                if category == '' or category == 'None':
                    category = None
                
                # Validate required fields
                if not question or not answer:
                    results["skipped"].append({
                        "row": index + 2,  # +2 because index starts at 0 and we have header
                        "reason": "Empty question or answer",
                        "question": question[:50] + "..." if len(question) > 50 else question
                    })
                    continue
                
                # Parse optional fields
                try:
                    sort_order = int(row.get('sort_order', 0)) if row.get('sort_order') and str(row.get('sort_order')).strip() else 0
                except (ValueError, TypeError):
                    sort_order = 0
                
                try:
                    is_published_value = row.get('is_published', '1')
                    if str(is_published_value).lower() in ['false', '0', 'no', 'n']:
                        is_published = 0
                    else:
                        is_published = 1
                except (ValueError, TypeError):
                    is_published = 1
                
                # Check if FAQ with same question already exists
                existing_faq = frappe.db.get_value("FAQ", {"question": question}, ["name", "answer"])
                
                if existing_faq:
                    # Update existing FAQ
                    faq_doc = frappe.get_doc("FAQ", existing_faq[0])
                    
                    # Check if content is different
                    content_changed = (
                        faq_doc.answer != answer or
                        faq_doc.category != category or
                        faq_doc.sort_order != sort_order or
                        faq_doc.is_published != is_published
                    )
                    
                    if content_changed:
                        faq_doc.answer = answer
                        faq_doc.category = category
                        faq_doc.sort_order = sort_order
                        faq_doc.is_published = is_published
                        faq_doc.save(ignore_permissions=True)
                        
                        results["updated"].append({
                            "row": index + 2,
                            "question": question[:100] + "..." if len(question) > 100 else question,
                            "faq_id": faq_doc.name,
                            "action": "updated"
                        })
                    else:
                        results["skipped"].append({
                            "row": index + 2,
                            "reason": "No changes detected",
                            "question": question[:50] + "..." if len(question) > 50 else question
                        })
                else:
                    # Create new FAQ
                    faq_doc = frappe.get_doc({
                        "doctype": "FAQ",
                        "question": question,
                        "answer": answer,
                        "category": category,
                        "sort_order": sort_order,
                        "is_published": is_published
                    })
                    
                    faq_doc.insert(ignore_permissions=True)
                    
                    results["created"].append({
                        "row": index + 2,
                        "question": question[:100] + "..." if len(question) > 100 else question,
                        "faq_id": faq_doc.name,
                        "action": "created"
                    })
                
            except Exception as e:
                results["errors"].append({
                    "row": index + 2,
                    "error": str(e),
                    "question": str(row.get('question', ''))[:50] + "..." if len(str(row.get('question', ''))) > 50 else str(row.get('question', ''))
                })
        
        # Commit all changes
        frappe.db.commit()
        
        # Prepare summary
        summary = {
            "total_rows": total_rows,
            "created": len(results["created"]),
            "updated": len(results["updated"]),
            "skipped": len(results["skipped"]),
            "errors": len(results["errors"])
        }
        
        return {
            "success": True,
            "message": f"FAQ import completed. Created: {summary['created']}, Updated: {summary['updated']}, Skipped: {summary['skipped']}, Errors: {summary['errors']}",
            "summary": summary,
            "details": results
        }
        
    except Exception as e:
        frappe.log_error(f"FAQ import error: {str(e)}", "FAQ Import")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Import failed: {str(e)}"
        }

@frappe.whitelist()
def get_faq_import_template():
    """
    Generate and return a CSV template file for FAQ import (without pandas dependency)
    """
    try:
        import csv
        import io
        
        # Create sample data
        sample_data = [
            {
                'question': 'What is a tradeline?',
                'answer': 'A tradeline is an account on your credit report. It can be a credit card, loan, mortgage, or other line of credit.',
                'category': 'General',
                'sort_order': '1',
                'is_published': '1'
            },
            {
                'question': 'How long does it take to see results?',
                'answer': 'Results typically appear on your credit report within 1-2 billing cycles, or approximately 30-60 days.',
                'category': 'Timeline', 
                'sort_order': '2',
                'is_published': '1'
            },
            {
                'question': 'Is this service legal?',
                'answer': 'Yes, being added as an authorized user is completely legal and has been used for decades.',
                'category': 'Legal',
                'sort_order': '3', 
                'is_published': '1'
            }
        ]
        
        # Create CSV content
        output = io.StringIO()
        if sample_data:
            fieldnames = sample_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_data)
        
        csv_content = output.getvalue()
        output.close()
        
        # Set response headers for file download
        frappe.local.response.filename = "faq_import_template.csv"
        frappe.local.response.filecontent = csv_content.encode('utf-8')
        frappe.local.response.type = "binary"
        frappe.local.response.headers["Content-Type"] = "text/csv; charset=utf-8"
        frappe.local.response.headers["Content-Disposition"] = 'attachment; filename="faq_import_template.csv"'
        
        return {
            "success": True,
            "message": "CSV template file generated successfully"
        }
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Failed to generate template: {str(e)}"
        }

@frappe.whitelist()
def bulk_delete_faqs(faq_ids):
    """
    Bulk delete FAQs
    """
    try:
        # Check permissions
        user = get_authenticated_user()
        if not user or not is_administrator(user):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Access denied. Admin privileges required."
            }
        
        if isinstance(faq_ids, str):
            import json
            faq_ids = json.loads(faq_ids)
        
        if not isinstance(faq_ids, list):
            return {
                "success": False,
                "message": "FAQ IDs must be provided as a list"
            }
        
        deleted_count = 0
        errors = []
        
        for faq_id in faq_ids:
            try:
                if frappe.db.exists("FAQ", faq_id):
                    frappe.delete_doc("FAQ", faq_id, ignore_permissions=True)
                    deleted_count += 1
                else:
                    errors.append(f"FAQ {faq_id} not found")
            except Exception as e:
                errors.append(f"Error deleting FAQ {faq_id}: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} FAQs successfully",
            "deleted_count": deleted_count,
            "errors": errors
        }
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Bulk delete failed: {str(e)}"
        }

# Testimonial APIs

@frappe.whitelist(allow_guest=True)
def get_testimonials(limit=20, start=0):
    """
    Get list of testimonials
    """
    try:
        # Convert limit and start to integers with validation
        try:
            limit = int(limit) if limit else 20
            start = int(start) if start else 0
        except (ValueError, TypeError):
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Invalid pagination parameters. 'limit' and 'start' must be valid integers."}
        
        filters = {"is_published": 1}
        
        # Get total count for pagination
        total_count = frappe.db.count("Testimonial", filters)
        
        testimonials = frappe.get_all("Testimonial",
            filters=filters,
            fields=["name", "customer_name", "testimonial", "rating", 
                   "customer_image", "sort_order"],
            limit=limit,
            start=start,
            order_by="sort_order asc, creation desc"
        )
        
        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0
        
        return {
            "success": True,
            "testimonials": testimonials,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_testimonial(customer_name, testimonial, rating=5, 
                      customer_email=None, customer_image=None, sort_order=0):
    """
    Create new testimonial
    """
    try:
        if not frappe.has_permission("Testimonial", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        testimonial_doc = frappe.get_doc({
            "doctype": "Testimonial",
            "customer_name": customer_name,
            "customer_email": customer_email,
            "testimonial": testimonial,
            "rating": rating,
            "customer_image": customer_image,
            "sort_order": sort_order,
            "is_published": 1
        })
        
        testimonial_doc.insert()
        
        return {
            "success": True,
            "message": "Testimonial created successfully",
            "testimonial": {
                "name": testimonial_doc.name,
                "customer_name": testimonial_doc.customer_name,
                "testimonial": testimonial_doc.testimonial
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_testimonial(name, customer_name=None, customer_email=None, testimonial=None, 
                      rating=None, customer_image=None, sort_order=None, 
                      is_published=None):
    """
    Update testimonial
    """
    try:
        if not frappe.has_permission("Testimonial", "write"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        testimonial_doc = frappe.get_doc("Testimonial", name)
        
        if customer_name:
            testimonial_doc.customer_name = customer_name
        if customer_email is not None:
            testimonial_doc.customer_email = customer_email
        if testimonial:
            testimonial_doc.testimonial = testimonial
        if rating is not None:
            testimonial_doc.rating = rating
        if customer_image:
            testimonial_doc.customer_image = customer_image
        if sort_order is not None:
            testimonial_doc.sort_order = sort_order
        if is_published is not None:
            testimonial_doc.is_published = is_published
        
        testimonial_doc.save()
        
        return {
            "success": True,
            "message": "Testimonial updated successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }
@frappe.whitelist(allow_guest=True)
@jwt_required()
def delete_testimonial(name):
    """
    Delete testimonial
    """
    try:
        if not frappe.has_permission("Testimonial", "delete"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        frappe.delete_doc("Testimonial", name)
        
        return {
            "success": True,
            "message": "Testimonial deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

# Page Content APIs

@frappe.whitelist(allow_guest=True)
def get_page_content(page_name=None, section_name=None):
    """
    Get page content
    """
    try:
        filters = {"is_active": 1}
        
        if page_name:
            filters["page_name"] = page_name
        if section_name:
            filters["section_name"] = section_name
        
        content = frappe.get_all("Page Content",
            filters=filters,
            fields=["name", "page_name", "section_name", "content", "content_type"],
            order_by="page_name asc, section_name asc"
        )
        
        return {
            "success": True,
            "content": content
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def update_page_content(page_name, section_name, content, content_type="Other"):
    """
    Update page content
    """
    try:
        if not frappe.has_permission("Page Content", "write"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        # Check if content already exists
        existing = frappe.get_all("Page Content", 
            filters={"page_name": page_name, "section_name": section_name},
            limit=1
        )
        
        if existing:
            content_doc = frappe.get_doc("Page Content", existing[0].name)
            content_doc.content = content
            content_doc.content_type = content_type
            content_doc.save()
        else:
            content_doc = frappe.get_doc({
                "doctype": "Page Content",
                "page_name": page_name,
                "section_name": section_name,
                "content": content,
                "content_type": content_type,
                "is_active": 1
            })
            content_doc.insert()
        
        return {
            "success": True,
            "message": "Page content updated successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }
