# RocketTradeLine - Mermaid Flow Diagrams

## Complete Purchase Flow

```mermaid
graph TD
    A[Customer Login] -->|JWT Token| B[Create Cart]
    B --> C{Cart Exists?}
    C -->|Yes| D[Get Existing Cart]
    C -->|No| E[Create New Cart]
    D --> F[Add Items to Cart]
    E --> F
    
    F -->|Select Tradelines| G[Add to Cart Items]
    G --> H{More Items?}
    H -->|Yes| G
    H -->|No| I[Review Cart]
    
    I --> J[Checkout Cart]
    J --> K{Pre-Checkout Validations}
    
    K -->|User Disabled| L[Error: 417 User Disabled]
    K -->|No Agreement| M[Error: 417 No Agreement]
    K -->|No Questionnaire| N[Error: 417 No Questionnaire]
    K -->|Slots Unavailable| O[Error: 409 Slot Conflict]
    K -->|All Valid ✓| P[Cart Status: Checked Out]
    
    P --> Q[Upload Proof of Payment 📎]
    Q --> R[Create Payment Request]
    R --> S[Payment Status: Pending]
    S --> T[Email to Admin 📧]
    
    T --> U[Admin Reviews Payment]
    U --> V{Payment Valid?}
    V -->|No| W[Reject Payment]
    V -->|Yes| X[Approve Payment]
    
    X --> Y[Status: Completed]
    Y --> Z[Create Client Tradelines]
    Z --> AA[Status: Pending AU]
    
    AA --> AB[Email to Cardholder 📧]
    AB --> AC[Cardholder Adds AU]
    AC --> AD[Upload Proof of AU 📎]
    AD --> AE[Admin Updates Status]
    AE --> AF[Status: Active ✅]
    
    AF --> AG[Email to Customer 📧]
    AG --> AH[Tradeline Reporting]
    AH --> AI[Credit Report Updated]

    style A fill:#667eea,stroke:#333,stroke-width:2px,color:#fff
    style AF fill:#48bb78,stroke:#333,stroke-width:3px,color:#fff
    style AI fill:#48bb78,stroke:#333,stroke-width:2px,color:#fff
    style L fill:#fc8181,stroke:#333,stroke-width:2px,color:#fff
    style M fill:#fc8181,stroke:#333,stroke-width:2px,color:#fff
    style N fill:#fc8181,stroke:#333,stroke-width:2px,color:#fff
    style O fill:#fc8181,stroke:#333,stroke-width:2px,color:#fff
```

---

## Status Transitions

```mermaid
stateDiagram-v2
    [*] --> CartActive: Create Cart
    CartActive --> CartCheckedOut: Checkout
    CartCheckedOut --> PaymentPending: Create Payment Request
    
    PaymentPending --> PaymentApproved: Admin Approves
    PaymentPending --> PaymentFailed: Validation Fails
    PaymentPending --> PaymentExpired: 24 Hours Pass
    
    PaymentApproved --> PaymentCompleted: Process Complete
    PaymentCompleted --> ClientTradeline_PendingAU: Create Client Tradelines
    
    ClientTradeline_PendingAU --> ClientTradeline_Active: Cardholder Adds AU
    ClientTradeline_Active --> ClientTradeline_Completed: 60 Days Expire
    ClientTradeline_Active --> ClientTradeline_RefundRequested: Customer Issues
    
    ClientTradeline_PendingAU --> ClientTradeline_Cancelled: Cancelled
    ClientTradeline_Active --> ClientTradeline_Removed: AU Removed
    
    PaymentFailed --> [*]
    PaymentExpired --> [*]
    ClientTradeline_Completed --> [*]
    ClientTradeline_Removed --> [*]
    
    note right of PaymentPending: Proof of Payment Required 📎
    note right of ClientTradeline_PendingAU: Awaiting AU Assignment
    note right of ClientTradeline_Active: Proof of AU Required 📎
```

---

## Email Notification Flow

```mermaid
sequenceDiagram
    participant C as Customer
    participant S as System
    participant A as Admin
    participant CH as Cardholder
    participant B as Broker

    C->>S: Create Payment Request
    S->>S: Upload Proof of Payment 📎
    S->>A: 📧 Payment Request Notification
    
    A->>S: Review & Approve Payment
    S->>S: Create Client Tradelines
    S->>S: Status: Pending AU
    
    alt Broker Assigned
        S->>B: 📧 Broker Action Required
        B->>CH: Forward AU Request
    else No Broker
        S->>CH: 📧 AU Assignment Notification
    end
    
    CH->>CH: Add AU to Account
    CH->>A: Send Proof of AU
    A->>S: Upload Proof 📎
    A->>S: Update Status: Active
    
    alt Broker Assigned
        S->>B: 📧 Active Status Notification
        B->>C: Forward Confirmation
    else No Broker
        S->>C: 📧 Active Status Notification
    end
    
    Note over S,C: Tradeline Active ✅
    Note over S,C: Reporting in 30-60 Days
```

---

## Data Relationship Diagram

```mermaid
erDiagram
    CUSTOMER ||--o{ TRADELINE_CART : "owns"
    CUSTOMER ||--o{ PAYMENT_REQUEST : "makes"
    CUSTOMER ||--o{ CLIENT_TRADELINES : "has"
    
    TRADELINE_CART ||--o{ CART_ITEM : "contains"
    TRADELINE_CART ||--|| PAYMENT_REQUEST : "generates"
    
    PAYMENT_REQUEST ||--o{ CLIENT_TRADELINES : "creates"
    PAYMENT_REQUEST ||--o{ FILE : "has proof_of_payment"
    
    CLIENT_TRADELINES ||--|| TRADELINE : "linked to"
    CLIENT_TRADELINES ||--o{ FILE : "has proof_of_au"
    
    TRADELINE ||--|| TRADELINE_BANK : "belongs to"
    TRADELINE ||--|| CUSTOMER : "owned by (cardholder)"
    
    CUSTOMER {
        string name PK
        string customer_name
        string email_id
        boolean has_signed_agreement
        boolean is_questionnaire_filled
        string account_manager FK
    }
    
    TRADELINE_CART {
        string name PK
        string user_id FK
        string customer FK
        string status
        string payment_mode
        datetime cart_expiry
        float total_amount
    }
    
    CART_ITEM {
        string parent FK
        string tradeline FK
        int quantity
        float rate
        float amount
    }
    
    PAYMENT_REQUEST {
        string name PK
        string cart_id FK
        string customer FK
        string payment_method
        float amount
        float fees
        float total_amount
        string status
        string approval_status
        string proof_of_payment
    }
    
    CLIENT_TRADELINES {
        string name PK
        string customer FK
        string cart FK
        string payment_request FK
        string tradeline FK
        int quantity
        float unit_price
        string status
        datetime created_date
        datetime expiry_date
    }
    
    TRADELINE {
        string name PK
        string bank FK
        string card_holder FK
        int max_spots
        int purchased_spots
        int remaining_spots
        string status
        float price
    }
```

---

## Slot Availability Check Flow

```mermaid
flowchart TD
    A[Customer Clicks Checkout] --> B[validate_cart_slots]
    
    B --> C{For Each Cart Item}
    C --> D[Get Tradeline]
    D --> E[Query Client Tradelines]
    
    E --> F{Sum All Active Quantities}
    F --> G[Statuses: Active, Inactive, Pending AU, Refund Requested]
    
    G --> H[Calculate: remaining = max_spots - total_purchased]
    H --> I{requested <= remaining?}
    
    I -->|No| J[Add to validation_errors]
    I -->|Yes| K{More Items?}
    
    K -->|Yes| C
    K -->|No| L{Any Errors?}
    
    L -->|Yes| M[Return 409 Conflict]
    L -->|No| N[Proceed with Checkout]
    
    J --> K
    
    M --> O[Display Error Details]
    O --> P[Show: tradeline_name, requested, available]
    
    N --> Q[Update Cart Status: Checked Out]
    Q --> R[Set payment_status: Pending]
    
    style M fill:#fc8181,stroke:#333,stroke-width:3px
    style N fill:#48bb78,stroke:#333,stroke-width:3px
    style B fill:#fbbf24,stroke:#333,stroke-width:2px
```

---

## File Attachment Flow

```mermaid
flowchart LR
    A[Customer Uploads File] --> B{File Type?}
    
    B -->|proof_of_payment| C[Create File Doctype]
    B -->|proof_of_au| D[Create File Doctype]
    
    C --> E[Set is_private = 1]
    D --> F[Set is_private = 1]
    
    E --> G[Link to Payment Request]
    F --> H[Link to Client Tradelines]
    
    G --> I[attached_to_doctype: Payment Request]
    G --> J[attached_to_name: PR-XXX]
    G --> K[attached_to_field: proof_of_payment]
    
    H --> L[attached_to_doctype: Client Tradelines]
    H --> M[attached_to_name: CT-XXX]
    H --> N[attached_to_field: proof_of_au_assignment]
    
    I --> O[File Stored]
    J --> O
    K --> O
    L --> P[File Stored]
    M --> P
    N --> P
    
    O --> Q[Admin Can View]
    P --> R[Admin Can View]
    
    style O fill:#48bb78,stroke:#333,stroke-width:2px
    style P fill:#48bb78,stroke:#333,stroke-width:2px
```

---

## Tradeline Spot Recalculation

```mermaid
flowchart TD
    A[Client Tradelines Event] --> B{Event Type?}
    
    B -->|Insert| C[after_insert Hook]
    B -->|Update Status| D[on_update Hook]
    B -->|Delete| E[after_delete Hook]
    
    C --> F[recalculate_tradeline_remaining_spots]
    D --> F
    E --> F
    
    F --> G[Get Parent Tradeline]
    G --> H[Query All Client Tradelines]
    
    H --> I[Filter by: tradeline = current_tradeline]
    I --> J[Filter by: status IN Active, Inactive, Pending AU, Refund Requested]
    
    J --> K[SUM quantities]
    K --> L[total_purchased = SUM]
    
    L --> M[remaining_spots = max_spots - total_purchased]
    M --> N{remaining_spots < 0?}
    
    N -->|Yes| O[Throw Error: Cannot Go Negative]
    N -->|No| P[Update Tradeline]
    
    P --> Q[Set purchased_spots]
    P --> R[Set remaining_spots]
    
    Q --> S[Add Comment to Tradeline]
    R --> S
    
    S --> T[Log Update]
    
    style O fill:#fc8181,stroke:#333,stroke-width:2px
    style T fill:#48bb78,stroke:#333,stroke-width:2px
    style F fill:#fbbf24,stroke:#333,stroke-width:2px
```

---

## API Security Flow

```mermaid
flowchart TD
    A[API Request] --> B{JWT Token Present?}
    
    B -->|No| C[Return 401 Unauthorized]
    B -->|Yes| D[Validate Token]
    
    D --> E{Token Valid?}
    E -->|No| F[Return 401 Invalid Token]
    E -->|Yes| G[Extract User from Token]
    
    G --> H{Resource Access Check}
    
    H -->|Cart| I{Cart Owner or Admin?}
    H -->|Payment| J{Payment Creator or Admin?}
    H -->|Client Tradeline| K{Customer or Admin?}
    
    I -->|No| L[Return 403 Access Denied]
    I -->|Yes| M[Grant Access]
    
    J -->|No| L
    J -->|Yes| M
    
    K -->|No| L
    K -->|Yes| M
    
    M --> N[Execute API Function]
    N --> O[Return Response]
    
    style C fill:#fc8181,stroke:#333,stroke-width:2px
    style F fill:#fc8181,stroke:#333,stroke-width:2px
    style L fill:#fc8181,stroke:#333,stroke-width:2px
    style O fill:#48bb78,stroke:#333,stroke-width:2px
```

---

## Checkout Validation Flow

```mermaid
flowchart TD
    A[Checkout Request] --> B{User Enabled?}
    B -->|No| C[Error 417: User Disabled]
    B -->|Yes| D{Signed Agreement?}
    
    D -->|No| E[Error 417: No Agreement]
    D -->|Yes| F{Questionnaire Filled?}
    
    F -->|No| G[Error 417: No Questionnaire]
    F -->|Yes| H{Cart Has Items?}
    
    H -->|No| I[Error: Empty Cart]
    H -->|Yes| J{Payment Mode Selected?}
    
    J -->|No| K[Error: No Payment Mode]
    J -->|Yes| L{Customer Info Present?}
    
    L -->|No| M[Error: No Customer]
    L -->|Yes| N[validate_cart_slots]
    
    N --> O{Slots Available?}
    O -->|No| P[Error 409: Slot Conflict]
    O -->|Yes| Q[All Validations Passed ✓]
    
    Q --> R[Update Cart Status]
    R --> S[status = Checked Out]
    R --> T[payment_status = Pending]
    
    S --> U[Success Response]
    T --> U
    
    style C fill:#fc8181,stroke:#333,stroke-width:2px
    style E fill:#fc8181,stroke:#333,stroke-width:2px
    style G fill:#fc8181,stroke:#333,stroke-width:2px
    style I fill:#fc8181,stroke:#333,stroke-width:2px
    style K fill:#fc8181,stroke:#333,stroke-width:2px
    style M fill:#fc8181,stroke:#333,stroke-width:2px
    style P fill:#fc8181,stroke:#333,stroke-width:2px
    style U fill:#48bb78,stroke:#333,stroke-width:3px
    style N fill:#fbbf24,stroke:#333,stroke-width:2px
```

---

## Payment Approval Workflow

```mermaid
sequenceDiagram
    participant C as Customer
    participant API as API Layer
    participant PR as Payment Request
    participant DB as Database
    participant Email as Email System
    participant A as Admin
    participant CT as Client Tradelines

    C->>API: create_manual_payment_request()
    API->>API: Upload proof_of_payment 📎
    API->>PR: Create Payment Request
    PR->>DB: Insert Record
    
    Note over PR: status = Pending<br/>approval_status = Pending Approval
    
    DB->>PR: Record Created
    PR->>Email: send_payment_request_notification_email()
    Email->>A: 📧 New Payment Request
    
    Note over A: Admin Reviews<br/>Proof of Payment 📎
    
    A->>PR: Update Fields
    Note over PR: approval_status = Approved<br/>status = Completed
    
    PR->>PR: on_update Hook
    PR->>PR: handle_status_change()
    
    alt Status = Completed OR Approved
        PR->>CT: create_client_tradelines()
        
        loop For Each Cart Item
            CT->>DB: Insert Client Tradelines
            Note over CT: status = Pending AU
            CT->>CT: after_insert Hook
            CT->>DB: Update Tradeline Spots
        end
        
        CT->>Email: send_payment_approval_email()
        
        alt Broker Assigned
            Email->>Broker: 📧 Broker Action Required
        else No Broker
            Note over Email: Email Disabled per Requirements
        end
    end
    
    Note over CT: Client Tradelines Created ✓
```

---

*These diagrams can be rendered using Mermaid-compatible tools like:*
- *GitHub Markdown*
- *Mermaid Live Editor (mermaid.live)*
- *VS Code with Mermaid extension*
- *Confluence, Notion, GitLab*
