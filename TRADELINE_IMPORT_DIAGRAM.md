# Tradeline Import System - Visual Diagrams

## 🎯 is_external Flag Implementation

### Overview Diagram

```mermaid
graph TB
    subgraph "Normal Purchase Flow"
        A1[Customer Creates Cart] --> A2[Adds Items]
        A2 --> A3[Checkout]
        A3 --> A4[Upload Payment Proof]
        A4 --> A5[Payment Request Created<br/>is_external = 0]
        A5 --> A6{Admin Approves?}
        A6 -->|Yes| A7[Client Tradeline Created<br/>is_external = 0]
        A7 --> A8[📧 Send AU Request Email]
        A8 --> A9[Upload AU Proof]
        A9 --> A10[Status = Active]
        A10 --> A11[📧 Send Active Email]
    end
    
    subgraph "Manual Import Flow"
        B1[Admin Creates Import] --> B2[Add Items One by One]
        B2 --> B3[Fill All Fields Manually]
        B3 --> B4[Submit Form]
        B4 --> B5[Validate Data]
        B5 --> B6{Valid?}
        B6 -->|Yes| B7[Create Customer<br/>is_external = 1]
        B7 --> B8[Create Cart<br/>is_external = 1]
        B8 --> B9[Create Payment Request<br/>is_external = 1]
        B9 --> B10[Create Client Tradeline<br/>is_external = 1]
        B10 --> B11{Check is_external}
        B11 -->|TRUE| B12[❌ Skip ALL Emails]
        B12 --> B13[Records Created Silently]
        B6 -->|No| B14[Log Error]
    end
    
    style A5 fill:#90EE90
    style A7 fill:#90EE90
    style B7 fill:#FFB6C1
    style B8 fill:#FFB6C1
    style B9 fill:#FFB6C1
    style B10 fill:#FFB6C1
    style A8 fill:#87CEEB
    style A11 fill:#87CEEB
    style B12 fill:#FFA07A
```

---

## 📊 Data Model Changes

### DocType Modifications

```mermaid
erDiagram
    CUSTOMER ||--o{ TRADELINE_CART : "creates"
    CUSTOMER {
        string name PK
        string customer_name
        string email_id
        boolean is_external "NEW FIELD"
        string mobile_no
        datetime creation
    }
    
    TRADELINE_CART ||--|| PAYMENT_REQUEST : "generates"
    TRADELINE_CART {
        string name PK
        string user_id FK
        string customer FK
        string status
        boolean is_external "NEW FIELD"
        float total_amount
        datetime cart_expiry
    }
    
    PAYMENT_REQUEST ||--o{ CLIENT_TRADELINES : "creates"
    PAYMENT_REQUEST {
        string name PK
        string cart_id FK
        string customer FK
        float amount
        string status
        string approval_status
        boolean is_external "NEW FIELD"
        string proof_of_payment
        datetime created_at
    }
    
    CLIENT_TRADELINES }o--|| TRADELINE : "uses"
    CLIENT_TRADELINES {
        string name PK
        string customer FK
        string cart FK
        string payment_request FK
        string tradeline FK
        int quantity
        float unit_price
        string discount_type "NEW FIELD"
        float discount_value "NEW FIELD"
        float discount_amount "NEW FIELD"
        float subtotal "NEW FIELD"
        float total_amount
        string status
        boolean is_external "NEW FIELD"
        string proof_of_au_assignment
        date expiry_date
    }
    
    TRADELINE_IMPORT ||--o{ TRADELINE_IMPORT_ITEM : "contains"
    TRADELINE_IMPORT {
        string name PK
        string import_title
        datetime import_date
        string import_status
        int total_records
        int successful_imports
        int failed_imports
        text validation_log
        text processing_log
    }
    
    TRADELINE_IMPORT_ITEM {
        string customer_email
        string customer_name
        string tradeline_id FK
        int quantity
        float unit_price
        string discount_type
        float discount_value
        datetime cart_created_date
        datetime payment_approved_date
        datetime au_added_date
        date expiry_date
        string payment_status
        string approval_status
        string client_tradeline_status
        string proof_of_payment_url
        string proof_of_au_url
        string import_status
        string error_message
        string created_customer_id
        string created_cart_id
        string created_payment_id
        string created_tradeline_id
    }
```

---

## 🔄 Email Suppression Flow

### Decision Tree

```mermaid
flowchart TD
    A[Email Trigger Event] --> B{Check DocType}
    B -->|Payment Request| C{Check is_external flag}
    B -->|Client Tradelines| D{Check is_external flag}
    B -->|Cart| E{Check is_external flag}
    
    C -->|is_external = 1| F[❌ Skip Email<br/>Log Suppression]
    C -->|is_external = 0| G[✅ Send Email<br/>Normal Flow]
    
    D -->|is_external = 1| F
    D -->|is_external = 0| H[✅ Send Email<br/>Normal Flow]
    
    E -->|is_external = 1| F
    E -->|is_external = 0| I[✅ Send Email<br/>Normal Flow]
    
    F --> J[Continue Processing<br/>Without Notification]
    G --> K[Email Sent Successfully]
    H --> L[Email Sent Successfully]
    I --> M[Email Sent Successfully]
    
    style F fill:#FFA07A
    style G fill:#90EE90
    style H fill:#90EE90
    style I fill:#90EE90
```

---

## 📋 Import Processing Workflow

### Step-by-Step Process

```mermaid
sequenceDiagram
    participant Admin
    participant TI as Tradeline Import
    participant Validator
    participant Creator
    participant Customer
    participant Cart
    participant Payment
    participant ClientTL as Client Tradelines
    participant Email as Email System
    
    Admin->>TI: Upload Excel & Save
    TI->>TI: Set status = "In Progress"
    
    loop For Each Import Item
        TI->>Validator: Validate Item Data
        Validator-->>TI: Validation Result
        
        alt Validation Success
            TI->>Creator: Process Import Item
            Creator->>Customer: Create/Get Customer (is_external=1)
            Customer-->>Creator: Customer ID
            
            Creator->>Cart: Create Cart (is_external=1)
            Cart-->>Creator: Cart ID
            
            Creator->>Payment: Create Payment Request (is_external=1)
            Payment-->>Creator: Payment ID
            
            Creator->>ClientTL: Create Client Tradelines (is_external=1)
            ClientTL-->>Creator: Client Tradeline ID
            
            ClientTL->>Email: Trigger Email Event
            Email->>Email: Check is_external flag
            Email-->>ClientTL: is_external=1, Skip Email ❌
            
            Creator-->>TI: Success ✅
            TI->>TI: Increment successful_imports
        else Validation Failed
            Validator-->>TI: Error Details
            TI->>TI: Increment failed_imports
            TI->>TI: Log Error Message
        end
    end
    
    TI->>TI: Set status = "Completed"
    TI-->>Admin: Import Summary
```

---

## 🔍 Discount Implementation Diagram

### Discount Calculation Flow

```mermaid
flowchart TD
    A[Client Tradeline Form] --> B{Discount Type Selected?}
    B -->|No| C[Calculate: total = quantity × unit_price]
    B -->|Yes| D{Which Type?}
    
    D -->|Percentage| E[Calculate: subtotal = quantity × unit_price<br/>discount_amount = subtotal × value / 100]
    D -->|Amount| F[Calculate: subtotal = quantity × unit_price<br/>discount_amount = value]
    
    E --> G[Validate: percentage ≤ 100%]
    F --> H[Validate: amount ≤ subtotal]
    
    G --> I{Valid?}
    H --> J{Valid?}
    
    I -->|Yes| K[Calculate: total = subtotal - discount_amount]
    I -->|No| L[Show Error: Percentage cannot exceed 100%]
    
    J -->|Yes| K
    J -->|No| M[Show Error: Amount cannot exceed subtotal]
    
    K --> N[Update Fields:<br/>- subtotal<br/>- discount_amount<br/>- total_amount]
    
    C --> O[Update total_amount]
    N --> P[Save Record]
    O --> P
    
    style K fill:#90EE90
    style L fill:#FFA07A
    style M fill:#FFA07A
    style P fill:#87CEEB
```

---

## 🚀 Complete Import Architecture

### System Overview

```mermaid
graph TB
    subgraph "Input Layer"
        A1[Admin Manual Entry]
        A2[Form Fields]
        A3[Child Table Rows]
    end
    
    subgraph "Import Layer"
        B1[Tradeline Import DocType]
        B2[Import Item Child Table]
        B3[File Attachment Handler]
    end
    
    subgraph "Validation Layer"
        C1[Required Fields Check]
        C2[Date Chronology Check]
        C3[Tradeline Availability Check]
        C4[Discount Validation]
        C5[Status Combination Check]
    end
    
    subgraph "Processing Layer"
        D1[Customer Creation/Link]
        D2[Cart Creation]
        D3[Payment Request Creation]
        D4[Client Tradeline Creation]
        D5[Attachment Processing]
    end
    
    subgraph "Flag Management"
        E1[Set is_external = 1]
        E2[Apply to Customer]
        E3[Apply to Cart]
        E4[Apply to Payment]
        E5[Apply to Client Tradeline]
    end
    
    subgraph "Email Control"
        F1{Check is_external}
        F2[Skip Payment Notification]
        F3[Skip AU Assignment Email]
        F4[Skip Active Status Email]
        F5[Skip Refund Email]
    end
    
    subgraph "Output Layer"
        G1[Success Log]
        G2[Error Log]
        G3[Created Records]
        G4[Import Summary]
    end
    
    A1 --> B2
    A2 --> B2
    A3 --> B2
    B2 --> B3
    
    B2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    
    C5 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    
    D1 --> E1
    E1 --> E2
    E1 --> E3
    E1 --> E4
    E1 --> E5
    
    D4 --> F1
    F1 -->|is_external=1| F2
    F1 -->|is_external=1| F3
    F1 -->|is_external=1| F4
    F1 -->|is_external=1| F5
    
    D5 --> G1
    C5 --> G2
    D5 --> G3
    G1 --> G4
    G2 --> G4
    G3 --> G4
    
    style E1 fill:#FFB6C1
    style F1 fill:#FFA07A
    style G4 fill:#90EE90
```

---

## 🎨 DocType Field Layout

### Tradeline Import DocType UI

```
┌─────────────────────────────────────────────────────────────────┐
│ Tradeline Import                          [IMP-00001] [Draft]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Import Title: Historical Purchase Import - October 2025_____  │
│  Import Date:  [2025-10-12 14:30:00]  Status: [Draft ▼]        │
│  Import Notes: Importing 3 historical purchases from legacy___ │
│                system for customer migration___________________  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Import Items                                          [+ Add Row]│
├─────────────────────────────────────────────────────────────────┤
│ Row 1:                                                           │
│  Customer Email*:  john@example.com_________________________    │
│  Customer Name*:   John Doe_________________________________    │
│  Tradeline*:       [TL-0001 ▼] Chase Bank - $15,000            │
│  Quantity*:        [2]      Unit Price*: [$150.00]              │
│  Cart Created*:    [2025-01-15 10:30:00]                        │
│  Payment Approved*:[2025-01-16 14:20:00]                        │
│  Payment Status*:  [Completed ▼]  Approval*: [Approved ▼]      │
│  Client Status*:   [Active ▼]                                   │
│  Discount Type:    [Percentage ▼]  Value: [10]                 │
│  Import Status:    [Pending]                                    │
│ ─────────────────────────────────────────────────────────────   │
│ Row 2:                                                           │
│  Customer Email*:  jane@example.com_________________________    │
│  Customer Name*:   Jane Smith_______________________________    │
│  Tradeline*:       [TL-0002 ▼] Bank of America - $20,000       │
│  Quantity*:        [1]      Unit Price*: [$200.00]              │
│  ...                                                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Import Summary (After Submit)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Total Records:     [3]          Successful: [3]                │
│  Failed Imports:    [0]                                         │
│                                                                  │
│  Validation Log:                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ✓ Row 1: john@example.com - Valid                       │  │
│  │ ✓ Row 2: jane@example.com - Valid                       │  │
│  │ ✓ Row 3: bob@example.com - Valid                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Processing Log:                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [14:30:01] Created customer: CUST-00001                  │  │
│  │ [14:30:02] Created cart: CART-0001                       │  │
│  │ [14:30:03] Created payment: PAY-CART-0001-IMPORT         │  │
│  │ [14:30:04] Created client tradeline: CTL-00001           │  │
│  │ [14:30:05] Skipped email (external import)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Settings                                                         │
├─────────────────────────────────────────────────────────────────┤
│  [☑] Suppress Emails (Always enabled for imports)              │
│                                                                  │
│  [Save]  [Submit]  [Cancel]                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Note: Submit button triggers import processing
      Save keeps as Draft for further editing
```

---

## 🔐 Security & Access Control

### Permission Matrix

```mermaid
graph TB
    subgraph "Roles & Permissions"
        A[System Manager] -->|Full Access| B[Tradeline Import]
        C[Administrator] -->|Full Access| B
        D[Broker] -->|No Access| B
        E[Customer] -->|No Access| B
        
        B --> F[Create Import]
        B --> G[Read Import]
        B --> H[Update Import]
        B --> I[Delete Import]
        B --> J[Process Import]
        
        F --> K[Sets is_external=1 on all records]
        J --> K
        K --> L[Suppresses ALL emails]
        L --> M[Records created silently]
    end
    
    style A fill:#90EE90
    style C fill:#90EE90
    style D fill:#FFA07A
    style E fill:#FFA07A
    style L fill:#FFB6C1
```

---

## 📊 Import Status States

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft: Create Import
    Draft --> InProgress: Save/Process
    InProgress --> Validating: Start Validation
    Validating --> Processing: Validation Pass
    Validating --> PartiallyCompleted: Some Items Failed
    Processing --> Completed: All Success
    Processing --> PartiallyCompleted: Some Failed
    Processing --> Failed: All Failed
    Completed --> [*]
    PartiallyCompleted --> [*]
    Failed --> Draft: Fix & Retry
    Draft --> [*]: Cancel
    
    note right of Validating
        Checks:
        - Required fields
        - Date chronology
        - Tradeline availability
        - Discount validity
    end note
    
    note right of Processing
        Creates:
        - Customer (is_external=1)
        - Cart (is_external=1)
        - Payment (is_external=1)
        - Client TL (is_external=1)
        Emails: SUPPRESSED ❌
    end note
```

---

## 🎯 Modified Email Functions

### Function Call Flow with is_external Check

```mermaid
flowchart LR
    A[Event Trigger] --> B{Function Called}
    
    B -->|Payment Created| C[send_payment_notification_email]
    B -->|Payment Approved| D[handle_status_change]
    B -->|AU Needed| E[send_au_assignment_email]
    B -->|Tradeline Active| F[send_active_status_notification_email]
    B -->|Refund Requested| G[send_refund_request_notification_email]
    B -->|Tradeline Removed| H[send_removal_confirmation_email]
    
    C --> I{Check is_external}
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    
    I -->|is_external = 1| J[Log: Skipping email for external import]
    I -->|is_external = 0| K[Send Email Normally]
    
    J --> L[Return Early]
    K --> M[Email Sent]
    
    style I fill:#FFD700
    style J fill:#FFA07A
    style K fill:#90EE90
```

---

*This diagram document complements TRADELINE_IMPORT_README.md*  
*Last Updated: October 12, 2025*
