# Token-Based Authentication for Rocket Tradeline API

This document describes how to use token-based authentication with the Rocket Tradeline API.

## Overview

The Rocket Tradeline API uses a secure token-based authentication system that provides authorization tokens instead of exposing raw API credentials. This approach enhances security by:

- Not exposing API keys and secrets directly
- Using encoded authorization tokens
- Supporting both Bearer token and traditional token formats

## Getting Started

### 1. User Registration

Register a new user to get an authorization token:

```bash
curl -X POST "https://your-domain.com/api/method/rockettradeline.api.auth.sign_up" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "secure_password",
    "phone": "+1234567890"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User and customer created successfully",
  "authorization_token": "YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ==",
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+1234567890"
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890"
  }
}
```

### 2. User Login

Login with existing credentials:

```bash
curl -X POST "https://your-domain.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -d '{
    "usr": "user@example.com",
    "pwd": "secure_password"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "authorization_token": "YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ==",
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "user_image": null,
    "phone": "+1234567890",
    "role_profile_name": null,
    "roles": ["Customer"]
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890"
  }
}
```

## Using Authorization Tokens

### Method 1: Bearer Token (Recommended)

Use the authorization token as a Bearer token in the Authorization header:

```bash
curl -X GET "https://your-domain.com/api/method/rockettradeline.api.auth.get_current_user" \
  -H "Authorization: Bearer YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ=="
```

### Method 2: Query Parameters

You can also pass the decoded token as query parameters:

```bash
# First decode the authorization token to get api_key:api_secret
# Then use it in the URL
curl "https://your-domain.com/api/method/rockettradeline.api.auth.get_current_user?api_key=your_api_key&api_secret=your_api_secret"
```

## Token Management

### Regenerate Authorization Token

If you need to regenerate your authorization token:

```bash
curl -X POST "https://your-domain.com/api/method/rockettradeline.api.auth.regenerate_tokens" \
  -H "Authorization: Bearer YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ=="
```

**Response:**
```json
{
  "success": true,
  "message": "New authorization token generated successfully",
  "authorization_token": "bmV3X2FwaV9rZXlfaGVyZTpuZXdfYXBpX3NlY3JldF9oZXJl"
}
```

### Validate Token

Check if your authorization token is valid:

```bash
curl -X POST "https://your-domain.com/api/method/rockettradeline.api.auth.validate_token" \
  -H "Authorization: Bearer YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ=="
```

### Revoke Tokens

Revoke all tokens for security:

```bash
curl -X POST "https://your-domain.com/api/method/rockettradeline.api.auth.revoke_tokens" \
  -H "Authorization: Bearer YXBpX2tleV9oZXJlOmFwaV9zZWNyZXRfaGVyZQ=="
```

## Authorization Token Format

The authorization token is a Base64-encoded string that contains the API key and secret in the format:
```
Base64Encode(api_key:api_secret)
```

This provides security benefits:
- API credentials are not exposed in plain text
- The token can be easily validated and decoded on the server
- Compatible with standard Bearer token authentication

## Error Handling

Common error responses:

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Invalid credentials"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "message": "Access denied"
}
```

### 400 Bad Request
```json
{
  "success": false,
  "message": "Invalid email address"
}
```

## Integration Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'https://your-domain.com/api/method/',
  headers: {
    'Authorization': `Bearer ${authorizationToken}`,
    'Content-Type': 'application/json'
  }
});

// Get current user
const user = await api.get('rockettradeline.api.auth.get_current_user');
```

### Python
```python
import requests
import base64

def make_api_request(endpoint, token, data=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://your-domain.com/api/method/{endpoint}'
    
    if data:
        response = requests.post(url, json=data, headers=headers)
    else:
        response = requests.get(url, headers=headers)
    
    return response.json()

# Usage
user_data = make_api_request('rockettradeline.api.auth.get_current_user', authorization_token)
```

## Security Best Practices

1. **Store tokens securely**: Never expose authorization tokens in client-side code
2. **Use HTTPS**: Always use HTTPS in production
3. **Token expiration**: Tokens expire after 30 days and should be regenerated
4. **Revoke compromised tokens**: If a token is compromised, revoke it immediately
5. **Environment variables**: Store tokens in environment variables, not in code

## Changelog

- **v1.0**: Initial implementation with authorization token support
- **v1.1**: Added Bearer token support for better compatibility
- **v1.2**: Enhanced security with Base64 encoding
