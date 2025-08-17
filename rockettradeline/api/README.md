# Rocket Tradeline API Documentation

## Base URL
All API endpoints are prefixed with: `https://rockettradline.com/api/method/rockettradeline.api`

## Authentication
Most endpoints require authentication. Include the session cookie or API key in requests.

### Authentication Methods
1. **Session Cookie**: After login, session cookies are automatically handled
2. **API Key**: Include `Authorization: token <api_key>:<api_secret>` header
3. **Basic Auth**: Include `Authorization: Basic <base64_encoded_credentials>` header

## Response Format
All responses follow this format:
```json
{
    "success": true/false,
    "message": "Response message",
    "data": {}  // Response data when success=true
}
```

## Error Codes
- **200**: Success
- **400**: Bad Request - Invalid parameters
- **401**: Unauthorized - Authentication required
- **403**: Forbidden - Insufficient permissions
- **404**: Not Found - Resource not found
- **500**: Internal Server Error - Server error

## Authentication APIs

### 1. Login
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth.login`

**Parameters:**
- `usr` (string): Email or username
- `pwd` (string): Password

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -d '{
    "usr": "user@example.com",
    "pwd": "password123"
  }'
```

**Response:**
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "name": "user@example.com",
        "email": "user@example.com",
        "full_name": "John Doe",
        "user_image": "/path/to/image.jpg",
        "roles": ["Customer"]
    }
}
```

### 2. Sign Up
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth.sign_up`

**Parameters:**
- `email` (string): User email
- `full_name` (string): Full name
- `password` (string, optional): Password

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.sign_up" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "full_name": "Jane Doe",
    "password": "newpassword123"
  }'
```

### 3. Google OAuth Login
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth_extended.google_oauth_login`

**Parameters:**
- `credential` (string): Google OAuth credential token

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth_extended.google_oauth_login" \
  -H "Content-Type: application/json" \
  -d '{
    "credential": "google_oauth_token_here"
  }'
```

### 4. Logout
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth.logout`

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.logout" \
  -H "Content-Type: application/json" \
  -b "cookies_from_login"
```

### 5. Get Current User
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.auth.get_current_user`

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.auth.get_current_user" \
  -H "Content-Type: application/json" \
  -b "cookies_from_login"
```

### 6. Update Profile
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth.update_profile`

**Parameters:**
- `full_name` (string, optional): Full name
- `phone` (string, optional): Phone number
- `user_image` (string, optional): User image URL

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.update_profile" \
  -H "Content-Type: application/json" \
  -b "cookies_from_login" \
  -d '{
    "full_name": "John Smith",
    "phone": "+1-555-123-4567"
  }'
```

### 7. Change Password
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth_extended.change_password`

**Parameters:**
- `old_password` (string): Current password
- `new_password` (string): New password

### 8. Forgot Password
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth_extended.forgot_password`

**Parameters:**
- `email` (string): User email

### 9. Reset Password
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth_extended.reset_password`

**Parameters:**
- `token` (string): Reset token from email
- `new_password` (string): New password

## User Management APIs (Admin Only)

### 10. Get Users
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.auth.get_users`

**Parameters:**
- `limit` (int, optional): Number of records (default: 20)
- `start` (int, optional): Offset (default: 0)
- `search` (string, optional): Search term

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.auth.get_users?limit=10&search=john" \
  -H "Content-Type: application/json" \
  -b "admin_cookies"
```

### 11. Update User
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.auth.update_user`

**Parameters:**
- `user_id` (string): User ID
- `full_name` (string, optional): Full name
- `enabled` (boolean, optional): Enable/disable user
- `roles` (array, optional): User roles

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.update_user" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "user_id": "user@example.com",
    "enabled": true,
    "roles": ["Customer", "Tradeline Manager"]
  }'
```

### 12. Delete User
**Endpoint:** `DELETE https://rockettradline.com/api/method/rockettradeline.api.auth.delete_user`

**Parameters:**
- `user_id` (string): User ID

**Request Example:**
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.auth.delete_user" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "user_id": "user@example.com"
  }'
```

## Tradeline APIs

### 13. Get Tradelines
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines`

**Parameters:**
- `limit` (int, optional): Number of records (default: 20)
- `start` (int, optional): Offset (default: 0)
- `search` (string, optional): Search term
- `filters` (json, optional): Additional filters
  - `min_price` (float): Minimum price
  - `max_price` (float): Maximum price
  - `min_credit_limit` (int): Minimum credit limit
  - `bank` (string): Bank name

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines?limit=10&filters=%7B%22min_price%22%3A100%2C%22bank%22%3A%22Chase%22%7D" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "tradelines": [
        {
            "name": "00001",
            "bank": "BANK-001",
            "bank_name": "Chase Bank",
            "age_year": 5,
            "age_month": 6,
            "credit_limit": 10000,
            "price": 500.00,
            "max_spots": 5,
            "remaining_spots": 3,
            "closing_date": 15,
            "credit_utilization_rate": 10.5,
            "status": "Active"
        }
    ]
}
```

### 14. Get Tradeline Details
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradeline`

**Parameters:**
- `tradeline_id` (string): Tradeline ID

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradeline?tradeline_id=00001" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "tradeline": {
        "name": "00001",
        "bank": "BANK-001",
        "bank_name": "Chase Bank",
        "age_year": 5,
        "age_month": 6,
        "credit_limit": 10000,
        "price": 500.00,
        "max_spots": 5,
        "remaining_spots": 3,
        "purchased_spots": 2,
        "closing_date": 15,
        "credit_utilization_rate": 10.5,
        "status": "Active",
        "balance": 1050.00,
        "card_holder": {
            "name": "CARD-001",
            "fullname": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567"
        },
        "mailing_address": {
            "name": "ADDR-001"
        }
    }
}
```

### 15. Create Tradeline
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.tradeline.create_tradeline`

**Parameters:**
- `bank` (string): Bank ID
- `age_year` (int): Age in years
- `credit_limit` (int): Credit limit
- `price` (float): Price
- `max_spots` (int): Maximum spots
- `closing_date` (int): Closing date (1-31)
- `card_holder` (string): Card holder ID
- `mailing_address` (string): Mailing address ID
- `age_month` (int, optional): Age in months
- `credit_utilization_rate` (float, optional): Credit utilization rate
- `balance` (float, optional): Balance
- `status` (string, optional): Status (default: "Active")

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.tradeline.create_tradeline" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "bank": "Chase Bank",
    "age_year": 5,
    "credit_limit": 10000,
    "price": 500.00,
    "max_spots": 5,
    "closing_date": 15,
    "card_holder": "John Doe",
    "mailing_address": "Sample Address",
    "age_month": 6,
    "credit_utilization_rate": 10.5,
    "balance": 1050.00
  }'
```

### 16. Update Tradeline
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.tradeline.update_tradeline`

**Parameters:**
- `tradeline_id` (string): Tradeline ID
- All other parameters from create_tradeline are optional

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.tradeline.update_tradeline" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "tradeline_id": "00001",
    "price": 550.00,
    "status": "Active"
  }'
```

### 17. Delete Tradeline
**Endpoint:** `DELETE https://rockettradline.com/api/method/rockettradeline.api.tradeline.delete_tradeline`

**Parameters:**
- `tradeline_id` (string): Tradeline ID

**Request Example:**
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.tradeline.delete_tradeline" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "tradeline_id": "00001"
  }'
```

### 18. Change Tradeline Status
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.tradeline.change_tradeline_status`

**Parameters:**
- `tradeline_id` (string): Tradeline ID
- `status` (string): New status ("Active" or "InActive")

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.tradeline.change_tradeline_status" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "tradeline_id": "00001",
    "status": "InActive"
  }'
```

### 19. Get Banks
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_banks`

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_banks" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "banks": [
        {
            "name": "Chase Bank",
            "bank_name": "Chase Bank"
        },
        {
            "name": "Bank of America",
            "bank_name": "Bank of America"
        }
    ]
}
```

### 20. Create Bank
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.tradeline.create_bank`

**Parameters:**
- `bank_name` (string): Bank name

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.tradeline.create_bank" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "bank_name": "Wells Fargo"
  }'
```

## Website Management APIs

### 21. Get Website Settings
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.website.get_website_settings`

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_website_settings" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "settings": {
        "name": "Rocket Tradeline",
        "title": "Rocket Tradeline - Premium Credit Enhancement",
        "description": "Professional tradeline services to boost your credit score",
        "meta_keywords": "tradeline, credit, authorized user, credit repair",
        "site_logo": "/files/logo.png",
        "favicon": "/files/favicon.ico",
        "footer_text": "© 2025 Rocket Tradeline. All rights reserved.",
        "contact_email": "info@rockettradeline.com",
        "contact_phone": "+1-800-123-4567",
        "facebook_url": "https://facebook.com/rockettradeline",
        "twitter_url": "https://twitter.com/rockettradeline",
        "linkedin_url": "https://linkedin.com/company/rockettradeline",
        "instagram_url": "https://instagram.com/rockettradeline"
    }
}
```

### 22. Update Website Settings
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.update_website_settings`

**Parameters:**
- `title` (string, optional): Website title
- `description` (string, optional): Website description
- `meta_keywords` (string, optional): Meta keywords
- `site_logo` (string, optional): Site logo URL
- `favicon` (string, optional): Favicon URL
- `footer_text` (string, optional): Footer text
- `contact_email` (string, optional): Contact email
- `contact_phone` (string, optional): Contact phone
- `facebook_url` (string, optional): Facebook URL
- `twitter_url` (string, optional): Twitter URL
- `linkedin_url` (string, optional): LinkedIn URL
- `instagram_url` (string, optional): Instagram URL

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.update_website_settings" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "title": "Rocket Tradeline - Premium Credit Solutions",
    "description": "Transform your credit profile with our expert tradeline services",
    "contact_email": "support@rockettradeline.com",
    "contact_phone": "+1-800-TRADELINE"
  }'
```

## FAQ APIs

### 23. Get FAQs
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.website.get_faqs`

**Parameters:**
- `category` (string, optional): Filter by category
- `limit` (int, optional): Number of records (default: 50)
- `start` (int, optional): Offset (default: 0)

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_faqs?category=General&limit=10" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "faqs": [
        {
            "name": "What is a tradeline?",
            "question": "What is a tradeline?",
            "answer": "A tradeline is a record of activity for any type of credit extended to you by a lender and reported to a credit reporting agency.",
            "category": "General",
            "sort_order": 1
        },
        {
            "name": "How long does it take to see results?",
            "question": "How long does it take to see results?",
            "answer": "Typically, you can see results within 30-45 days after being added as an authorized user.",
            "category": "Timeline",
            "sort_order": 2
        }
    ]
}
```

### 24. Create FAQ
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.create_faq`

**Parameters:**
- `question` (string): FAQ question
- `answer` (string): FAQ answer
- `category` (string, optional): Category
- `sort_order` (int, optional): Sort order (default: 0)

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.create_faq" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "question": "How much does it cost?",
    "answer": "Our pricing varies based on the tradeline selected. Contact us for current rates.",
    "category": "Pricing",
    "sort_order": 5
  }'
```

### 25. Update FAQ
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.update_faq`

**Parameters:**
- `faq_id` (string): FAQ ID
- `question` (string, optional): FAQ question
- `answer` (string, optional): FAQ answer
- `category` (string, optional): Category
- `sort_order` (int, optional): Sort order
- `is_published` (boolean, optional): Publication status

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.update_faq" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "faq_id": "What is a tradeline?",
    "answer": "Updated answer: A tradeline is a comprehensive record of your credit account activity...",
    "sort_order": 1
  }'
```

### 26. Delete FAQ
**Endpoint:** `DELETE https://rockettradline.com/api/method/rockettradeline.api.website.delete_faq`

**Parameters:**
- `faq_id` (string): FAQ ID

**Request Example:**
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.website.delete_faq" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "faq_id": "What is a tradeline?"
  }'
```

## Testimonial APIs

### 27. Get Testimonials
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.website.get_testimonials`

**Parameters:**
- `limit` (int, optional): Number of records (default: 20)
- `start` (int, optional): Offset (default: 0)

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_testimonials?limit=5" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "testimonials": [
        {
            "name": "Sarah Johnson",
            "customer_name": "Sarah Johnson",
            "testimonial": "Rocket Tradeline helped me increase my credit score by 120 points in just 2 months!",
            "rating": 5,
            "customer_image": "/files/sarah_johnson.jpg",
            "sort_order": 1
        },
        {
            "name": "Mike Chen",
            "customer_name": "Mike Chen",
            "testimonial": "Professional service and excellent results. Highly recommended!",
            "rating": 5,
            "customer_image": "/files/mike_chen.jpg",
            "sort_order": 2
        }
    ]
}
```

### 28. Create Testimonial
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.create_testimonial`

**Parameters:**
- `customer_name` (string): Customer name
- `testimonial` (string): Testimonial text
- `rating` (int, optional): Rating 1-5 (default: 5)
- `customer_image` (string, optional): Customer image URL
- `sort_order` (int, optional): Sort order (default: 0)

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.create_testimonial" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "customer_name": "Jennifer Martinez",
    "testimonial": "Amazing service! My credit score improved significantly within weeks.",
    "rating": 5,
    "customer_image": "/files/jennifer_martinez.jpg",
    "sort_order": 3
  }'
```

### 29. Update Testimonial
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.update_testimonial`

**Parameters:**
- `testimonial_id` (string): Testimonial ID
- `customer_name` (string, optional): Customer name
- `testimonial` (string, optional): Testimonial text
- `rating` (int, optional): Rating 1-5
- `customer_image` (string, optional): Customer image URL
- `sort_order` (int, optional): Sort order
- `is_published` (boolean, optional): Publication status

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.update_testimonial" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "testimonial_id": "Sarah Johnson",
    "testimonial": "Updated testimonial: Rocket Tradeline exceeded my expectations...",
    "rating": 5
  }'
```

### 30. Delete Testimonial
**Endpoint:** `DELETE https://rockettradline.com/api/method/rockettradeline.api.website.delete_testimonial`

**Parameters:**
- `testimonial_id` (string): Testimonial ID

**Request Example:**
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.website.delete_testimonial" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "testimonial_id": "Sarah Johnson"
  }'
```

## Page Content APIs

### 31. Get Page Content
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.website.get_page_content`

**Parameters:**
- `page_name` (string, optional): Filter by page name
- `section_name` (string, optional): Filter by section name

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_page_content?page_name=homepage&section_name=hero" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "content": [
        {
            "name": "homepage",
            "page_name": "homepage",
            "section_name": "hero",
            "content": "<h1>Transform Your Credit Score</h1><p>Professional tradeline services to boost your creditworthiness</p>",
            "content_type": "Hero Section"
        },
        {
            "name": "homepage-features",
            "page_name": "homepage",
            "section_name": "features",
            "content": "<div class='features'>Our premium features...</div>",
            "content_type": "Feature Section"
        }
    ]
}
```

### 32. Update Page Content
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.website.update_page_content`

**Parameters:**
- `page_name` (string): Page name
- `section_name` (string): Section name
- `content` (string): Content text
- `content_type` (string, optional): Content type (default: "Other")

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.update_page_content" \
  -H "Content-Type: application/json" \
  -b "admin_cookies" \
  -d '{
    "page_name": "homepage",
    "section_name": "hero",
    "content": "<h1>Boost Your Credit Score Fast</h1><p>Professional authorized user tradelines for rapid credit improvement</p>",
    "content_type": "Hero Section"
  }'
```

## File Management APIs

### 33. Upload File
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.files.upload_file`

**Form Data Parameters:**
- `file`: File to upload (multipart/form-data)
- `doctype` (string, optional): Document type to attach to
- `docname` (string, optional): Document name to attach to
- `folder` (string, optional): Folder to save in (default: "Home")
- `is_private` (int, optional): 1 for private, 0 for public (default: 0)

**Base64 Parameters:**
- `file_content` (string): Base64 encoded file content
- `filename` (string): Original filename
- `doctype` (string, optional): Document type to attach to
- `docname` (string, optional): Document name to attach to
- `folder` (string, optional): Folder to save in
- `is_private` (int, optional): 1 for private, 0 for public

**Form Data Upload Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.files.upload_file" \
  -H "Content-Type: multipart/form-data" \
  -b "cookies.txt" \
  -F "file=@/path/to/document.pdf" \
  -F "folder=Documents" \
  -F "is_private=1"
```

**Base64 Upload Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.files.upload_file" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b "cookies.txt" \
  -d "file_content=data:application/pdf;base64,JVBERi0xLjQKMSAwIG9..." \
  -d "filename=document.pdf" \
  -d "folder=Documents" \
  -d "is_private=1"
```

**Response:**
```json
{
    "success": true,
    "message": "File uploaded successfully",
    "file": {
        "name": "file-id-123",
        "file_name": "document.pdf",
        "file_url": "/files/document.pdf",
        "file_size": 12345,
        "is_private": 1,
        "content_hash": "abc123def456"
    }
}
```

### 34. Upload Multiple Files
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.files.upload_multiple_files`

**Form Data Parameters:**
- Multiple file fields with different names
- Same optional parameters as single upload

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.files.upload_multiple_files" \
  -H "Content-Type: multipart/form-data" \
  -b "cookies.txt" \
  -F "file1=@/path/to/document1.pdf" \
  -F "file2=@/path/to/image.jpg" \
  -F "file3=@/path/to/spreadsheet.xlsx" \
  -F "folder=Uploads" \
  -F "is_private=0"
```

**Response:**
```json
{
    "success": true,
    "message": "Uploaded 3 files successfully",
    "uploaded_files": [
        {
            "name": "file-id-123",
            "file_name": "document1.pdf",
            "file_url": "/files/document1.pdf",
            "file_size": 12345,
            "is_private": 0
        },
        {
            "name": "file-id-124",
            "file_name": "image.jpg",
            "file_url": "/files/image.jpg",
            "file_size": 67890,
            "is_private": 0
        }
    ],
    "errors": []
}
```

### 35. Get File Information
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.files.get_file_info`

**Parameters:**
- `file_name` (string): File ID to get information for

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.files.get_file_info?file_name=file-id-123" \
  -H "Content-Type: application/json" \
  -b "cookies.txt"
```

**Response:**
```json
{
    "success": true,
    "file": {
        "name": "file-id-123",
        "file_name": "document.pdf",
        "file_url": "/files/document.pdf",
        "file_size": 12345,
        "content_type": "application/pdf",
        "is_private": 1,
        "folder": "Documents",
        "attached_to_doctype": null,
        "attached_to_name": null,
        "creation": "2025-08-12 10:30:00",
        "modified": "2025-08-12 10:30:00",
        "owner": "user@example.com"
    }
}
```

### 36. Download File
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.files.download_file`

**Parameters:**
- `file_name` (string): File ID to download

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.files.download_file?file_name=file-id-123" \
  -b "cookies.txt" \
  -o downloaded_file.pdf
```

**Response:**
- Binary file content with appropriate headers
- Content-Type: application/pdf (or appropriate MIME type)
- Content-Disposition: attachment; filename="document.pdf"

### 37. Get Files List
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.files.get_files_list`

**Parameters:**
- `doctype` (string, optional): Filter by document type
- `docname` (string, optional): Filter by document name
- `folder` (string, optional): Filter by folder
- `is_private` (int, optional): Filter by privacy (1 or 0)
- `limit` (int, optional): Number of files to return (default: 50, max: 100)
- `start` (int, optional): Offset for pagination (default: 0)
- `search` (string, optional): Search in file names

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.files.get_files_list?folder=Documents&limit=20&search=contract" \
  -H "Content-Type: application/json" \
  -b "cookies.txt"
```

**Response:**
```json
{
    "success": true,
    "files": [
        {
            "name": "file-id-123",
            "file_name": "contract.pdf",
            "file_url": "/files/contract.pdf",
            "file_size": 12345,
            "content_type": "application/pdf",
            "is_private": 1,
            "folder": "Documents",
            "attached_to_doctype": null,
            "attached_to_name": null,
            "creation": "2025-08-12 10:30:00",
            "modified": "2025-08-12 10:30:00",
            "owner": "user@example.com"
        }
    ],
    "total_count": 1,
    "limit": 20,
    "start": 0
}
```

### 38. Delete File
**Endpoint:** `DELETE https://rockettradline.com/api/method/rockettradeline.api.files.delete_file`

**Parameters:**
- `file_name` (string): File ID to delete

**Request Example:**
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.files.delete_file" \
  -H "Content-Type: application/json" \
  -b "cookies.txt" \
  -d '{
    "file_name": "file-id-123"
  }'
```

**Response:**
```json
{
    "success": true,
    "message": "File deleted successfully"
}
```

### 39. Create Folder
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.files.create_folder`

**Parameters:**
- `folder_name` (string): Name of the new folder
- `parent_folder` (string, optional): Parent folder (default: "Home")

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.files.create_folder" \
  -H "Content-Type: application/json" \
  -b "cookies.txt" \
  -d '{
    "folder_name": "Customer Documents",
    "parent_folder": "Home"
  }'
```

**Response:**
```json
{
    "success": true,
    "message": "Folder created successfully",
    "folder": {
        "name": "folder-id-456",
        "file_name": "Customer Documents",
        "folder": "Home"
    }
}
```

### 40. Get Folders List
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.files.get_folders`

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.files.get_folders" \
  -H "Content-Type: application/json" \
  -b "cookies.txt"
```

**Response:**
```json
{
    "success": true,
    "folders": [
        {
            "name": "folder-id-456",
            "file_name": "Customer Documents",
            "folder": "Home",
            "creation": "2025-08-12 11:00:00",
            "modified": "2025-08-12 11:00:00"
        },
        {
            "name": "folder-id-457",
            "file_name": "Reports",
            "folder": "Home",
            "creation": "2025-08-12 11:15:00",
            "modified": "2025-08-12 11:15:00"
        }
    ]
}
```

### 41. Get File by URL
**Endpoint:** `GET https://rockettradline.com/api/method/rockettradeline.api.files.get_file_by_url`

**Parameters:**
- `file_url` (string): File URL to get information for

**Request Example:**
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.files.get_file_by_url?file_url=/files/document.pdf" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "file": {
        "name": "file-id-123",
        "file_name": "document.pdf",
        "file_url": "/files/document.pdf",
        "file_size": 12345,
        "content_type": "application/pdf",
        "is_private": 0,
        "folder": "Home",
        "creation": "2025-08-12 10:30:00",
        "modified": "2025-08-12 10:30:00"
    }
}
```

### 42. Resize Image (Optional)
**Endpoint:** `POST https://rockettradline.com/api/method/rockettradeline.api.files.resize_image`

**Parameters:**
- `file_name` (string): Image file ID to resize
- `width` (int, optional): New width in pixels
- `height` (int, optional): New height in pixels
- `maintain_aspect_ratio` (boolean, optional): true/false (default: true)

**Note:** Requires Pillow library to be installed.

**Request Example:**
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.files.resize_image" \
  -H "Content-Type: application/json" \
  -b "cookies.txt" \
  -d '{
    "file_name": "image-file-id-789",
    "width": 300,
    "height": 200,
    "maintain_aspect_ratio": true
  }'
```

**Response:**
```json
{
    "success": true,
    "message": "Image resized successfully",
    "original_file": {
        "name": "image-file-id-789",
        "dimensions": "800x600"
    },
    "resized_file": {
        "name": "resized-image-id-790",
        "file_name": "image_resized_300x225.jpg",
        "file_url": "/files/image_resized_300x225.jpg",
        "dimensions": "300x225"
    }
}
```

## File Management Configuration

### File Upload Limits
Configure in site_config.json:
```json
{
    "max_file_size": 26214400,
    "allowed_file_extensions": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".rtf", ".csv",
        ".zip", ".rar", ".7z",
        ".mp4", ".avi", ".mov", ".wmv",
        ".mp3", ".wav", ".ogg"
    ]
}
```

### File Security Features

1. **Permission Control**: Files respect Frappe's role-based permissions
2. **Private Files**: Private files are only accessible by authorized users
3. **Secure Filenames**: Filenames are sanitized to prevent directory traversal
4. **Content Validation**: File types and sizes are validated
5. **Access Logging**: File access is logged for security auditing

### File Organization

- **Folders**: Organize files in a hierarchical folder structure
- **Attachments**: Attach files to specific documents (DocType instances)
- **Privacy**: Mark files as private or public
- **Metadata**: Track file owner, creation time, and modification time

## Error Handling

All endpoints return appropriate HTTP status codes and error messages:

### Common Error Responses

#### 400 Bad Request
```json
{
    "success": false,
    "message": "Invalid parameters provided",
    "error_code": "INVALID_PARAMS"
}
```

#### 401 Unauthorized
```json
{
    "success": false,
    "message": "Authentication required",
    "error_code": "AUTH_REQUIRED"
}
```

#### 403 Forbidden
```json
{
    "success": false,
    "message": "Permission denied",
    "error_code": "PERMISSION_DENIED"
}
```

#### 404 Not Found
```json
{
    "success": false,
    "message": "Resource not found",
    "error_code": "NOT_FOUND"
}
```

#### 500 Internal Server Error
```json
{
    "success": false,
    "message": "Internal server error",
    "error_code": "INTERNAL_ERROR"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- **Unauthenticated requests**: 100 requests per hour per IP
- **Authenticated requests**: 1000 requests per hour per user
- **Admin requests**: 5000 requests per hour per user

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

## Pagination

List endpoints support pagination:
- `limit`: Number of records per page (max 100)
- `start`: Offset for pagination (0-based)

Response includes pagination metadata:
```json
{
    "success": true,
    "data": [...],
    "pagination": {
        "total_count": 150,
        "limit": 20,
        "start": 0,
        "has_next": true,
        "has_prev": false,
        "current_page": 1,
        "total_pages": 8
    }
}
```

## Examples

### Complete Authentication Flow
```bash
# 1. Sign up new user
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.sign_up" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "full_name": "New User",
    "password": "securepassword123"
  }'

# 2. Login
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "usr": "newuser@example.com",
    "pwd": "securepassword123"
  }'

# 3. Get current user (using saved cookies)
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.auth.get_current_user" \
  -H "Content-Type: application/json" \
  -b cookies.txt

# 4. Update profile
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.update_profile" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "full_name": "Updated Name",
    "phone": "+1-555-987-6543"
  }'
```

### Search and Filter Tradelines
```bash
# Search tradelines with filters
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines" \
  -H "Content-Type: application/json" \
  -G \
  -d "limit=10" \
  -d "start=0" \
  -d "search=chase" \
  -d "filters={\"min_price\":200,\"max_price\":1000,\"min_credit_limit\":5000}"
```

### Create Complete Tradeline
```bash
# First get available banks
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_banks" \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt

# Create new tradeline
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.tradeline.create_tradeline" \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "bank": "Chase Bank",
    "age_year": 7,
    "age_month": 3,
    "credit_limit": 15000,
    "price": 750.00,
    "max_spots": 3,
    "closing_date": 10,
    "card_holder": "John Doe",
    "mailing_address": "Sample Address",
    "credit_utilization_rate": 5.5,
    "balance": 825.00,
    "status": "Active"
  }'
```

### Manage Website Content
```bash
# Update homepage hero section
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.update_page_content" \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "page_name": "homepage",
    "section_name": "hero",
    "content": "<div class=\"hero\"><h1>Premium Credit Enhancement</h1><p>Boost your credit score with our professional tradeline services</p><button class=\"cta-button\">Get Started Today</button></div>",
    "content_type": "Hero Section"
  }'

# Add new FAQ
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.create_faq" \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "question": "How quickly will I see results?",
    "answer": "Most clients see credit score improvements within 30-45 days of being added as an authorized user to a tradeline.",
    "category": "Timeline",
    "sort_order": 1
  }'

# Create testimonial
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.website.create_testimonial" \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "customer_name": "Alex Rodriguez",
    "testimonial": "Rocket Tradeline helped me qualify for my dream home mortgage. My credit score increased by 140 points in just 6 weeks!",
    "rating": 5,
    "customer_image": "/files/alex_rodriguez.jpg",
    "sort_order": 1
  }'
```

## Security Best Practices

1. **HTTPS Only**: All API calls must use HTTPS
2. **Authentication**: Always authenticate requests for protected endpoints
3. **Input Validation**: Validate all input parameters
4. **Rate Limiting**: Respect rate limits to avoid being blocked
5. **Error Handling**: Implement proper error handling in your client
6. **Logging**: Log API calls for debugging and monitoring
7. **Secure Storage**: Store API credentials securely

## SDKs and Libraries

### JavaScript/Node.js
```javascript
const RocketTradelineAPI = require('rockettradeline-api');

const api = new RocketTradelineAPI({
  baseUrl: 'https://rockettradline.com',
  apiKey: 'your-api-key'
});

// Login
const loginResult = await api.auth.login('user@example.com', 'password');

// Get tradelines
const tradelines = await api.tradeline.list({ limit: 10 });

// Create FAQ
const faq = await api.website.createFAQ({
  question: 'How does it work?',
  answer: 'Our process is simple...'
});
```

### Python
```python
import requests

class RocketTradelineAPI:
    def __init__(self, base_url='https://rockettradline.com'):
        self.base_url = base_url
        self.session = requests.Session()
    
    def login(self, email, password):
        response = self.session.post(
            f'{self.base_url}/api/method/rockettradeline.api.auth.login',
            json={'usr': email, 'pwd': password}
        )
        return response.json()
    
    def get_tradelines(self, limit=20, filters=None):
        params = {'limit': limit}
        if filters:
            params['filters'] = json.dumps(filters)
        
        response = self.session.get(
            f'{self.base_url}/api/method/rockettradeline.api.tradeline.get_tradelines',
            params=params
        )
        return response.json()

# Usage
api = RocketTradelineAPI()
login_result = api.login('user@example.com', 'password')
tradelines = api.get_tradelines(limit=10)
```

## Support

For API support and questions:
- **Email**: dev@rockettradeline.com
- **Documentation**: https://rockettradline.com/docs/api
- **Status Page**: https://status.rockettradline.com
- **GitHub Issues**: https://github.com/rockettradeline/api-issues

## Changelog

### v1.1.0 (2025-08-12)
- **NEW**: File Management APIs (10 new endpoints)
  - File upload (single and multiple files)
  - File download and access control
  - File information retrieval
  - File and folder management
  - Image resizing capabilities
  - Base64 and form-data upload support
  - Advanced permission controls for private files
- **IMPROVED**: Enhanced security for file operations
- **ADDED**: Comprehensive file validation and error handling

### v1.0.0 (2025-07-16)
- Initial API release
- 32 endpoints covering authentication, tradelines, and website management
- Role-based access control
- Rate limiting and pagination
- Comprehensive error handling
