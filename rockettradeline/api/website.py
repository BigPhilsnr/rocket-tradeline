from rockettradeline.api.auth import jwt_required, get_current_user
import frappe
from frappe import _
import json

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
def set_site_content(key, value, section, page, content_type="Text"):
    """
    Set site content by key, create if not exists
    """
    try:
        user = get_current_user()
        if not user or not frappe.has_permission("Site Content", "write"):
            return {
                "success": False,
                "message": "Permission denied"
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

@frappe.whitelist()
def bulk_set_site_content(content_list):
    """
    Bulk set site content - accepts list of content items
    Format: [{"key": "key1", "value": "value1", "section": "section1", "page": "page1", "content_type": "Text"}, ...]
    """
    user = get_current_user()
    if not user or not frappe.has_permission("Site Content", "write"):
        frappe.local.response.http_status_code = 403
        return {
            "success": False,
            "message": "Permission denied"
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
                content_doc.save()
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
                content_doc.insert()
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

@frappe.whitelist()
def delete_site_content(key):
    """
    Delete site content by key
    """
    user = frappe.session.user
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
    user = frappe.session.user
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
        filters = {"is_published": 1}
        
        if category:
            filters["category"] = category
        
        faqs = frappe.get_all("FAQ",
            filters=filters,
            fields=["name", "question", "answer", "category", "sort_order"],
            limit=limit,
            start=start,
            order_by="sort_order asc, creation asc"
        )
        
        return {
            "success": True,
            "faqs": faqs
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

@frappe.whitelist()
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

@frappe.whitelist()
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

# Testimonial APIs

@frappe.whitelist(allow_guest=True)
def get_testimonials(limit=20, start=0):
    """
    Get list of testimonials
    """
    try:
        testimonials = frappe.get_all("Testimonial",
            filters={"is_published": 1},
            fields=["name", "customer_name", "testimonial", "rating", 
                   "customer_image", "sort_order"],
            limit=limit,
            start=start,
            order_by="sort_order asc, creation desc"
        )
        
        return {
            "success": True,
            "testimonials": testimonials
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_testimonial(customer_name, testimonial, rating=5, 
                      customer_image=None, sort_order=0):
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

@frappe.whitelist()
def update_testimonial(testimonial_id, customer_name=None, testimonial=None, 
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
        
        testimonial_doc = frappe.get_doc("Testimonial", testimonial_id)
        
        if customer_name:
            testimonial_doc.customer_name = customer_name
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

@frappe.whitelist()
def delete_testimonial(testimonial_id):
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
        
        frappe.delete_doc("Testimonial", testimonial_id)
        
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
