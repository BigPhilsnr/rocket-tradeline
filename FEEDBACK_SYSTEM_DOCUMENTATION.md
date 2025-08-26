# RocketTradeline Feedback System Documentation

## Overview
The Feedback System provides a comprehensive questionnaire and lead capture solution for RocketTradeline. It allows potential customers to submit their tradeline needs through a structured form while providing admin tools for managing and following up on submissions.

## System Components

### 1. **DocType: Tradeline Feedback**
- **Purpose:** Store and manage customer feedback submissions
- **Location:** `rockettradeline/doctype/tradeline_feedback/`
- **Naming:** TLF-.YYYY.-.##### (e.g., TLF-2025-00001)

#### **Fields:**
- **Basic Info:** feedback_id, naming_series, submission_date
- **Questions:** question_1_why_buying, question_2_importance, question_3_timeline
- **Contact:** first_name, last_name, email, phone
- **Tracking:** ip_address, user_agent, source, status

### 2. **Web Form: Tradeline Feedback**
- **URL:** `/feedback` or `/tradeline-feedback`
- **Access:** Public (no login required)
- **Features:** Responsive design, validation, confirmation messages

### 3. **API Module: feedback.py**
- **Location:** `rockettradeline/api/feedback.py`
- **Purpose:** REST APIs for form submission and admin management

## Questionnaire Structure

Based on the provided JSON structure, the form includes:

### **Question 1: Why are you looking to buy a tradeline?**
- Type: Single choice
- Options:
  - I want to buy a home or property
  - I want to refinance a mortgage
  - I want to buy a car
  - I want to apply for a personal or business loan
  - Other reasons (e.g., rent a house)

### **Question 2: How important would you say it is to get to your score goals?**
- Type: Single choice
- Options:
  - Very Important
  - Important
  - Unimportant

### **Question 3: What's a realistic timeline to reach your target score?**
- Type: Single choice
- Options:
  - Urgent (within 30 days)
  - Next 1–2 months (31–60 days)
  - No rush (over 60 days)

### **Question 4: The Best Way to Reach You**
- Type: Contact form
- Fields:
  - First Name (required)
  - Last Name (required)
  - Email (required)
  - Phone Number (optional)

## API Endpoints

### **Public APIs (Guest Access)**

#### 1. Get Form Configuration
```http
GET /api/method/rockettradeline.api.feedback.get_feedback_form_config
```
**Purpose:** Retrieve form structure and validation rules
**Response:** Form configuration with questions and field definitions

#### 2. Submit Feedback
```http
POST /api/method/rockettradeline.api.feedback.submit_feedback
```
**Purpose:** Submit completed feedback form
**Body:**
```json
{
    "question_1_why_buying": "I want to buy a home or property",
    "question_2_importance": "Very Important",
    "question_3_timeline": "Urgent (within 30 days)",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "source": "Website Form"
}
```

### **Admin APIs (Authentication Required)**

#### 3. Get Feedback Submissions
```http
GET /api/method/rockettradeline.api.feedback.get_feedback_submissions
```
**Parameters:** limit, start, status, search
**Purpose:** List and filter feedback submissions

#### 4. Get Feedback Details
```http
GET /api/method/rockettradeline.api.feedback.get_feedback_details
```
**Parameters:** feedback_id
**Purpose:** Get detailed information about specific submission

#### 5. Update Feedback Status
```http
POST /api/method/rockettradeline.api.feedback.update_feedback_status
```
**Body:**
```json
{
    "feedback_id": "uuid-here",
    "status": "Contacted",
    "notes": "Initial contact made"
}
```
**Purpose:** Update submission status and add notes

#### 6. Get Statistics
```http
GET /api/method/rockettradeline.api.feedback.get_feedback_statistics
```
**Purpose:** Retrieve analytics and submission statistics

## Status Workflow

### **Status Options:**
1. **New** - Just submitted, awaiting review
2. **Contacted** - Initial contact made with customer
3. **Converted** - Customer became a paying client
4. **Closed** - No longer pursuing or completed

### **Workflow Process:**
1. Customer submits form → Status: "New"
2. Admin reviews and contacts → Status: "Contacted"
3. Customer purchases tradeline → Status: "Converted"
4. Lead completed/closed → Status: "Closed"

## Email Notifications

### **Admin Notifications:**
- Triggered on new submission
- Sent to system managers
- Contains submission details and quick links

### **Customer Confirmations:**
- Automatic confirmation email to submitter
- Contains submission ID and next steps
- Professional branded template

## Frontend Integration

### **React/Vue.js Example:**
```javascript
// Get form configuration
const getFormConfig = async () => {
    const response = await fetch('/api/method/rockettradeline.api.feedback.get_feedback_form_config');
    return response.json();
};

// Submit feedback
const submitFeedback = async (formData) => {
    const response = await fetch('/api/method/rockettradeline.api.feedback.submit_feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });
    return response.json();
};
```

### **HTML Form Example:**
```html
<form id="feedback-form">
    <h3>Why are you looking to buy a tradeline?</h3>
    <select name="question_1_why_buying" required>
        <option value="">Select an option...</option>
        <option value="I want to buy a home or property">Buy a home or property</option>
        <option value="I want to refinance a mortgage">Refinance a mortgage</option>
        <option value="I want to buy a car">Buy a car</option>
        <option value="I want to apply for a personal or business loan">Personal or business loan</option>
        <option value="Other reasons (e.g., rent a house)">Other reasons</option>
    </select>
    
    <!-- Additional questions... -->
    
    <h3>Contact Information</h3>
    <input type="text" name="first_name" placeholder="First Name" required>
    <input type="text" name="last_name" placeholder="Last Name" required>
    <input type="email" name="email" placeholder="Email" required>
    <input type="tel" name="phone" placeholder="Phone Number">
    
    <button type="submit">Submit Feedback</button>
</form>
```

## Admin Dashboard Integration

### **Dashboard Widgets:**
- Total submissions count
- New submissions this week
- Conversion rate
- Status distribution chart

### **Management Features:**
- Filter by status, date range, source
- Search by name, email, or content
- Bulk status updates
- Export to CSV
- Lead scoring based on urgency and importance

## Analytics & Reporting

### **Key Metrics:**
- **Purpose Distribution:** Why customers want tradelines
- **Urgency Analysis:** Timeline preferences
- **Importance Levels:** Goal importance ratings
- **Conversion Tracking:** Lead to customer conversion
- **Source Attribution:** Traffic source analysis

### **Reports Available:**
1. **Daily Submission Report**
2. **Weekly Performance Summary**
3. **Monthly Conversion Analysis**
4. **Purpose & Timeline Trends**
5. **Lead Quality Scoring**

## Security & Privacy

### **Data Protection:**
- Email validation and sanitization
- IP address logging for security
- Secure form submission (HTTPS)
- GDPR-compliant data handling

### **Permissions:**
- **Guest:** Can submit forms only
- **Customer:** Can view own submissions
- **Manager:** Can view and update all submissions
- **Admin:** Full access including statistics

## Installation & Setup

### **1. Install DocType:**
```bash
# Run the patch
bench migrate
```

### **2. Configure Email:**
Update email settings for notifications:
- SMTP configuration
- Email templates
- Notification recipients

### **3. Frontend Integration:**
- Embed web form or use API
- Customize styling to match brand
- Test form submission flow

### **4. Admin Training:**
- Review admin dashboard
- Train on status management
- Set up follow-up procedures

## Testing

### **Automated Tests:**
Run the test script:
```bash
python3 test_feedback_apis.py
```

### **Manual Testing:**
1. Submit test feedback via web form
2. Verify admin notifications
3. Test status updates
4. Check analytics accuracy

## Troubleshooting

### **Common Issues:**
1. **Form submission fails:** Check validation and required fields
2. **No email notifications:** Verify SMTP settings
3. **Permission errors:** Check user roles and permissions
4. **Missing data:** Ensure all API parameters are provided

### **Debug Mode:**
Enable developer mode for detailed error logging:
```python
frappe.conf.developer_mode = 1
```

## Future Enhancements

### **Planned Features:**
- Integration with CRM systems
- Advanced analytics dashboard
- A/B testing for form variations
- Automated follow-up email sequences
- Lead scoring algorithms
- Mobile app integration

### **Customization Options:**
- Additional question types
- Conditional logic in forms
- Custom validation rules
- Branded email templates
- Custom status workflows

## Support

For technical support and questions:
- **Documentation:** This file and API docs
- **Test Script:** `test_feedback_apis.py`
- **Email:** dev@rockettradeline.com
- **Issues:** GitHub repository issues section
