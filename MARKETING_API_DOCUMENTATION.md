# RocketTradeline Marketing API Documentation

## Overview
The Marketing API provides comprehensive email group management and newsletter subscription functionality for the RocketTradeline platform. These APIs allow guest users to subscribe to newsletters and provide admin functionality for managing email groups and subscribers.

## Base URL
```
Production: https://rockettradeline.com/api/method/rockettradeline.api.marketing
```

## API Endpoints

### 1. Newsletter Subscription (Guest Allowed)

#### Subscribe to Newsletter
**Endpoint:** `POST /subscribe_to_newsletter`
**Guest Access:** ✅ Allowed

Automatically adds users to the "Website Subscribers" email group.

**Parameters:**
- `email` (string, required): Valid email address
- `full_name` (string, optional): Full name of the subscriber

**Request Example:**
```bash
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.marketing.subscribe_to_newsletter" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe"
  }'
```

**Response Example:**
```json
{
  "success": true,
  "message": "Successfully subscribed to newsletter!",
  "email": "user@example.com",
  "group": "Website Subscribers",
  "status": "subscribed",
  "full_name": "John Doe"
}
```

#### Check Newsletter Subscription
**Endpoint:** `POST /check_newsletter_subscription`
**Guest Access:** ✅ Allowed

Check if an email is subscribed to the newsletter.

**Parameters:**
- `email` (string, required): Email address to check

**Request Example:**
```bash
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.marketing.check_newsletter_subscription" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response Example:**
```json
{
  "success": true,
  "email": "user@example.com",
  "subscribed": true,
  "status": "subscribed"
}
```

#### Unsubscribe from Newsletter
**Endpoint:** `POST /unsubscribe_from_newsletter`
**Guest Access:** ✅ Allowed

Unsubscribe a user from the newsletter.

**Parameters:**
- `email` (string, required): Email address to unsubscribe
- `token` (string, optional): Unsubscribe token (for future implementation)

**Request Example:**
```bash
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.marketing.unsubscribe_from_newsletter" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response Example:**
```json
{
  "success": true,
  "message": "Successfully unsubscribed from newsletter",
  "email": "user@example.com",
  "group": "Website Subscribers",
  "status": "unsubscribed"
}
```

### 2. Flexible Email Group Management (Guest Allowed)

#### Subscribe to Any Email Group
**Endpoint:** `POST /subscribe_to_email_group`
**Guest Access:** ✅ Allowed

Add user to any specified email group.

**Parameters:**
- `email` (string, required): Valid email address
- `email_group` (string, required): Name of the email group
- `full_name` (string, optional): Full name of the subscriber

**Request Example:**
```bash
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.marketing.subscribe_to_email_group" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "email_group": "Product Updates",
    "full_name": "John Doe"
  }'
```

**Response Example:**
```json
{
  "success": true,
  "message": "Successfully subscribed to Product Updates!",
  "email": "user@example.com",
  "group": "Product Updates",
  "status": "subscribed",
  "full_name": "John Doe"
}
```

### 3. Admin APIs (Authentication Required)

#### Get Newsletter Subscribers
**Endpoint:** `GET /get_newsletter_subscribers`
**Authentication:** 🔒 Required

Get paginated list of newsletter subscribers.

**Parameters:**
- `limit` (int, optional): Number of subscribers per page (default: 50)
- `start` (int, optional): Starting offset for pagination (default: 0)

**Request Example:**
```bash
curl -X GET "https://rockettradeline.com/api/method/rockettradeline.api.marketing.get_newsletter_subscribers?limit=20&start=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response Example:**
```json
{
  "success": true,
  "subscribers": [
    {
      "email": "user1@example.com",
      "creation": "2025-08-21 10:30:00",
      "modified": "2025-08-21 10:30:00"
    },
    {
      "email": "user2@example.com",
      "creation": "2025-08-21 09:15:00",
      "modified": "2025-08-21 09:15:00"
    }
  ],
  "total_count": 150,
  "limit": 20,
  "start": 0,
  "group": "Website Subscribers"
}
```

#### Get All Email Groups
**Endpoint:** `GET /get_email_groups`
**Authentication:** 🔒 Required

Get list of all email groups with subscriber counts.

**Request Example:**
```bash
curl -X GET "https://rockettradeline.com/api/method/rockettradeline.api.marketing.get_email_groups" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response Example:**
```json
{
  "success": true,
  "email_groups": [
    {
      "name": "Website Subscribers",
      "title": "Website Subscribers",
      "description": "Subscribers to RocketTradeline website newsletter and updates",
      "creation": "2025-08-21 08:00:00",
      "modified": "2025-08-21 08:00:00",
      "subscriber_count": 150
    },
    {
      "name": "Product Updates",
      "title": "Product Updates",
      "description": "Updates about new products and features",
      "creation": "2025-08-21 09:00:00",
      "modified": "2025-08-21 09:00:00",
      "subscriber_count": 75
    }
  ],
  "total_groups": 2
}
```

#### Create Email Group
**Endpoint:** `POST /create_email_group`
**Authentication:** 🔒 Required

Create a new email group.

**Parameters:**
- `title` (string, required): Title of the email group
- `description` (string, optional): Description of the email group

**Request Example:**
```bash
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.marketing.create_email_group" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "VIP Customers",
    "description": "Exclusive updates for VIP customers"
  }'
```

**Response Example:**
```json
{
  "success": true,
  "message": "Email group 'VIP Customers' created successfully",
  "email_group": {
    "name": "VIP Customers",
    "title": "VIP Customers",
    "description": "Exclusive updates for VIP customers"
  }
}
```

## Features

### ✅ Automatic Email Group Creation
- The "Website Subscribers" group is automatically created if it doesn't exist
- Seamless user experience without setup requirements

### ✅ Duplicate Subscription Handling
- Gracefully handles attempts to subscribe already subscribed emails
- Supports resubscription of previously unsubscribed users
- Clear status messages for all scenarios

### ✅ Email Validation
- Validates email format before processing
- Prevents invalid email addresses from being added

### ✅ User Information Updates
- If a User record exists, updates their information when provided
- Automatically splits full names into first/last name components

### ✅ Error Handling & Logging
- Comprehensive error logging for debugging
- User-friendly error messages
- Graceful fallback handling

### ✅ Permission Management
- Guest access for subscription operations
- Proper permission checks for admin operations
- Role-based access control

## Response Statuses

### Subscription Statuses
- `subscribed`: New subscription created
- `already_subscribed`: Email was already subscribed
- `resubscribed`: Previously unsubscribed email was resubscribed
- `unsubscribed`: Email was successfully unsubscribed
- `not_subscribed`: Email is not subscribed

### Common Error Responses
```json
{
  "success": false,
  "message": "Please provide a valid email address"
}
```

```json
{
  "success": false,
  "message": "Email group 'NonExistent Group' does not exist"
}
```

```json
{
  "success": false,
  "message": "Insufficient permissions to view subscribers"
}
```

## Integration Examples

### Frontend Newsletter Signup Form
```javascript
async function subscribeToNewsletter(email, fullName) {
  const response = await fetch('/api/method/rockettradeline.api.marketing.subscribe_to_newsletter', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      full_name: fullName
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    alert('Successfully subscribed to newsletter!');
  } else {
    alert('Subscription failed: ' + result.message);
  }
}
```

### Admin Dashboard Integration
```javascript
async function getNewsletterStats() {
  const response = await fetch('/api/method/rockettradeline.api.marketing.get_newsletter_subscribers', {
    headers: {
      'Authorization': 'Bearer ' + authToken
    }
  });
  
  const result = await response.json();
  
  if (result.success) {
    document.getElementById('subscriber-count').textContent = result.total_count;
    // Render subscriber list
    renderSubscriberList(result.subscribers);
  }
}
```

## Security Considerations

- ✅ Email validation prevents malformed input
- ✅ Permission checks for admin operations
- ✅ Rate limiting should be implemented at the web server level
- ✅ Email addresses are not exposed to unauthorized users
- ✅ Proper error handling prevents information leakage

## Testing

Use the provided test script to verify API functionality:

```bash
python3 test_newsletter_apis.py
```

The test script verifies all endpoints and provides comprehensive status reporting.

## Support

For API support and questions:
- **Email**: dev@rockettradeline.com
- **Documentation**: https://rockettradeline.com/docs/api
- **GitHub Issues**: https://github.com/rockettradeline/api-issues
