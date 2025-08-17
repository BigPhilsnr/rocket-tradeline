# Rocket Tradeline API Refe| POST | `/auth.get_users` | List users (Admin) | Yes |
| POST | `/auth.update_user` | Update user (Admin) | Yes |
| DELETE | `/auth.delete_user` | Delete user (Admin) | Yes |
| POST | `/auth.create_customer_for_user` | Create customer for user (Admin) | Yes |ce

## Quick Start

Base URL: `https://rockettradline.com/api/method/rockettradeline.api`

### Authentication
```bash
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -d '{"usr": "user@example.com", "pwd": "password123"}'
```

### Get Tradelines
```bash
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines?limit=10"
```

## API Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth.login` | User login | No |
| POST | `/auth.sign_up` | User registration | No |
| POST | `/auth.logout` | User logout | Yes |
| GET | `/auth.get_current_user` | Get current user | Yes |
| POST | `/auth.update_profile` | Update user profile | Yes |
| GET | `/auth.get_users` | List users (Admin) | Yes |
| POST | `/auth.update_user` | Update user (Admin) | Yes |
| DELETE | `/auth.delete_user` | Delete user (Admin) | Yes |
| GET | `/tradeline.get_tradelines` | List tradelines | No |
| GET | `/tradeline.get_tradeline` | Get tradeline details | No |
| POST | `/tradeline.create_tradeline` | Create tradeline | Yes |
| POST | `/tradeline.update_tradeline` | Update tradeline | Yes |
| DELETE | `/tradeline.delete_tradeline` | Delete tradeline | Yes |
| POST | `/tradeline.change_tradeline_status` | Change status | Yes |
| GET | `/tradeline.get_banks` | List banks | No |
| POST | `/tradeline.create_bank` | Create bank | Yes |
| GET | `/website.get_site_content` | Get site content | No |
| GET | `/website.get_content_by_key` | Get content by key | No |
| POST | `/website.set_site_content` | Set/update content | Yes |
| POST | `/website.bulk_set_site_content` | Bulk set content | Yes |
| DELETE | `/website.delete_site_content` | Delete content | Yes |
| GET | `/website.get_website_settings` | Get website settings (legacy) | No |
| POST | `/website.update_website_settings` | Update website settings (legacy) | Yes |
| GET | `/website.get_faqs` | List FAQs | No |
| POST | `/website.create_faq` | Create FAQ | Yes |
| POST | `/website.update_faq` | Update FAQ | Yes |
| DELETE | `/website.delete_faq` | Delete FAQ | Yes |
| GET | `/website.get_testimonials` | List testimonials | No |
| POST | `/website.create_testimonial` | Create testimonial | Yes |
| POST | `/website.update_testimonial` | Update testimonial | Yes |
| DELETE | `/website.delete_testimonial` | Delete testimonial | Yes |
| GET | `/website.get_page_content` | Get page content | No |
| POST | `/website.update_page_content` | Update page content | Yes |

## Authentication & Authorization

### Roles
- **Guest**: Can view public content (tradelines, FAQs, testimonials, etc.)
- **Customer**: Can manage their own profile
- **Tradeline Manager**: Can manage tradelines and banks
- **Website Manager**: Can manage website content
- **System Manager**: Full access to all features

### Session Management
After successful login, session cookies are set automatically. Include these cookies in subsequent requests.

## Data Models

### User
```json
{
  "name": "user@example.com",
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+1-555-123-4567",
  "user_image": "/files/user.jpg",
  "enabled": true,
  "roles": ["Customer"]
}
```

### Customer
```json
{
  "name": "CUST-00001",
  "customer_name": "John Doe",
  "customer_type": "Individual",
  "email_id": "user@example.com",
  "mobile_no": "+1-555-123-4567",
  "territory": "All Territories",
  "user": "user@example.com"
}
```

### User with Customer
```json
{
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+1-555-123-4567",
    "user_image": "/files/user.jpg",
    "roles": ["Customer"]
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1-555-123-4567"
  }
}
```

### Tradeline
```json
{
  "name": "00001",
  "bank": "Chase Bank",
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
  "balance": 1050.00,
  "status": "Active",
  "card_holder": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-123-4567"
  }
}
```

### Site Content
```json
{
  "name": "hero_title",
  "key": "hero_title",
  "value": "Boost Your Credit Score with Our Tradelines",
  "section": "hero",
  "page": "landing",
  "content_type": "Text",
  "is_active": true
}
```

### FAQ
```json
{
  "name": "what-is-a-tradeline",
  "question": "What is a tradeline?",
  "answer": "A tradeline is a record of activity for any type of credit...",
  "category": "General",
  "is_published": true,
  "sort_order": 1
}
```

### Testimonial
```json
{
  "name": "sarah-johnson",
  "customer_name": "Sarah Johnson",
  "testimonial": "Rocket Tradeline helped me increase my credit score...",
  "rating": 5,
  "customer_image": "/files/sarah.jpg",
  "is_published": true,
  "sort_order": 1
}
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| AUTH_REQUIRED | Authentication required | User must be logged in |
| PERMISSION_DENIED | Permission denied | User lacks required permissions |
| INVALID_PARAMS | Invalid parameters | Request parameters are invalid |
| NOT_FOUND | Resource not found | Requested resource doesn't exist |
| VALIDATION_ERROR | Validation error | Data validation failed |
| INTERNAL_ERROR | Internal server error | Server encountered an error |

## Rate Limits

- **Guest Users**: 100 requests/hour
- **Authenticated Users**: 1,000 requests/hour  
- **Admin Users**: 5,000 requests/hour

## Example Usage Patterns

### Frontend Integration (React)
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://rockettradline.com/api/method/rockettradeline.api',
  withCredentials: true
});

// Login
const login = async (email, password) => {
  const response = await api.post('.auth.login', {
    usr: email,
    pwd: password
  });
  return response.data;
};

// Get tradelines with filters
const getTradelines = async (filters = {}) => {
  const response = await api.get('.tradeline.get_tradelines', {
    params: { 
      limit: 20,
      filters: JSON.stringify(filters)
    }
  });
  return response.data;
};
```

### Backend Integration (Node.js)
```javascript
const express = require('express');
const axios = require('axios');

const app = express();
const rocketAPI = axios.create({
  baseURL: 'https://rockettradline.com/api/method/rockettradeline.api'
});

app.get('/api/tradelines', async (req, res) => {
  try {
    const response = await rocketAPI.get('.tradeline.get_tradelines', {
      params: req.query
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Testing

### Postman Collection
A complete Postman collection is available for testing all endpoints:
```json
{
  "info": {
    "name": "Rocket Tradeline API",
    "description": "Complete API collection for Rocket Tradeline"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "https://rockettradline.com/api/method/rockettradeline.api"
    }
  ]
}
```

### Test Environment
- **Production**: https://rockettradline.com
- **Staging**: https://staging.rockettradline.com
- **Test Page**: https://rockettradline.com/api-test.html

## Site Content API Details

### Get Site Content
```bash
curl "https://rockettradline.com/api/method/rockettradeline.api.website.get_site_content?section=hero&page=landing"
```

Response:
```json
{
  "success": true,
  "content": [
    {
      "key": "hero_title",
      "value": "Boost Your Credit Score with Our Tradelines",
      "section": "hero",
      "page": "landing",
      "content_type": "Text"
    }
  ]
}
```

### Get Content by Key
```bash
curl "https://rockettradline.com/api/method/rockettradeline.api.website.get_content_by_key?key=hero_title"
```

Response:
```json
{
  "success": true,
  "key": "hero_title",
  "value": "Boost Your Credit Score with Our Tradelines",
  "content_type": "Text"
}
```

### Set Site Content
```bash
curl -X POST https://rockettradline.com/api/method/rockettradeline.api.website.set_site_content \
  -H "Content-Type: application/json" \
  -d '{
    "key": "hero_title",
    "value": "Boost Your Credit Score with Our Tradelines",
    "section": "hero",
    "page": "landing",
    "content_type": "Text"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Site content created successfully",
  "content": {
    "key": "hero_title",
    "value": "Boost Your Credit Score with Our Tradelines",
    "section": "hero",
    "page": "landing",
    "content_type": "Text"
  }
}
```

### Bulk Set Site Content
```bash
curl -X POST https://rockettradline.com/api/method/rockettradeline.api.website.bulk_set_site_content \
  -H "Content-Type: application/json" \
  -d '{
    "content_list": [
      {
        "key": "hero_title",
        "value": "Boost Your Credit Score",
        "section": "hero",
        "page": "landing",
        "content_type": "Text"
      },
      {
        "key": "hero_subtitle",
        "value": "Get authorized user tradelines",
        "section": "hero",
        "page": "landing",
        "content_type": "Text"
      }
    ]
  }'
```

Response:
```json
{
  "success": true,
  "message": "Processed 2 items successfully, 0 errors",
  "results": [
    {
      "key": "hero_title",
      "action": "created",
      "success": true
    },
    {
      "key": "hero_subtitle",
      "action": "updated",
      "success": true
    }
  ],
  "errors": []
}
```

### Delete Site Content
```bash
curl -X DELETE "https://rockettradline.com/api/method/rockettradeline.api.website.delete_site_content?key=hero_title"
```

Response:
```json
{
  "success": true,
  "message": "Site content with key 'hero_title' deleted successfully"
}
```

### Content Types
- **Text**: Plain text content
- **HTML**: HTML formatted content
- **JSON**: JSON structured data
- **Image**: Image file URLs
- **Link**: URL links

### Common Content Patterns
```json
{
  "page": "landing",
  "sections": {
    "hero": ["hero_title", "hero_subtitle", "hero_image"],
    "features": ["feature_1_title", "feature_1_desc", "feature_2_title"],
    "testimonials": ["testimonial_heading", "testimonial_subheading"],
    "footer": ["footer_text", "copyright_text"]
  }
}
```

## WebSocket Support (Future)

Real-time updates for tradeline status changes:
```javascript
const socket = io('https://rockettradline.com');

socket.on('tradeline:status_changed', (data) => {
  console.log('Tradeline status updated:', data);
});
```

## API Versioning

Current version: v1.0.0

Version is included in response headers:
```
X-API-Version: 1.0.0
```

## Support Resources

- **Documentation**: https://docs.rockettradline.com
- **API Status**: https://status.rockettradline.com
- **Support Email**: api-support@rockettradline.com
- **Developer Portal**: https://developer.rockettradline.com

## Changelog

### v1.0.0 (2025-07-16)
- Initial API release
- 32 endpoints covering full platform functionality
- Role-based access control
- Comprehensive error handling
- Rate limiting and pagination
- Interactive test interface
