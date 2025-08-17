# Rocket Tradeline API Integration Guide

## Base URL
**Production**: `https://rockettradline.com/api/method/rockettradeline.api`

## Quick Integration Steps

### 1. Authentication
```bash
# Login to get session cookies
curl -X POST "https://rockettradline.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "usr": "your-email@example.com",
    "pwd": "your-password"
  }'
```

### 2. Get Tradelines
```bash
# Get all available tradelines
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines" \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

### 3. Filter Tradelines
```bash
# Filter by price range and bank
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.tradeline.get_tradelines" \
  -H "Content-Type: application/json" \
  -G \
  -d "filters={\"min_price\":200,\"max_price\":800,\"bank\":\"Chase Bank\"}"
```

### 4. Get Website Content
```bash
# Get FAQs
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_faqs" \
  -H "Content-Type: application/json"

# Get testimonials
curl -X GET "https://rockettradline.com/api/method/rockettradeline.api.website.get_testimonials" \
  -H "Content-Type: application/json"
```

## Common Integration Patterns

### Frontend (React/Vue/Angular)
```javascript
// API client setup
const API_BASE = 'https://rockettradline.com/api/method/rockettradeline.api';

class RocketTradelineClient {
  async login(email, password) {
    const response = await fetch(`${API_BASE}.auth.login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usr: email, pwd: password })
    });
    return response.json();
  }

  async getTradelines(filters = {}) {
    const params = new URLSearchParams();
    if (Object.keys(filters).length > 0) {
      params.append('filters', JSON.stringify(filters));
    }
    
    const response = await fetch(`${API_BASE}.tradeline.get_tradelines?${params}`, {
      credentials: 'include'
    });
    return response.json();
  }
}
```

### Backend (Node.js/Python/PHP)
```javascript
// Node.js example
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://rockettradline.com/api/method/rockettradeline.api',
  withCredentials: true
});

// Proxy endpoint
app.get('/api/tradelines', async (req, res) => {
  try {
    const response = await client.get('.tradeline.get_tradelines', {
      params: req.query
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Response Format
All endpoints return JSON in this format:
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { /* response data */ }
}
```

## Error Handling
```javascript
const handleAPIResponse = async (response) => {
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.message || 'API request failed');
  }
  
  return data;
};
```

## Testing
Visit `https://rockettradline.com/api-test.html` for an interactive API testing interface.

## Support
- Email: api-support@rockettradline.com
- Documentation: See full API_REFERENCE.md for complete details
