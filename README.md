# Multi-Agent Procurement System

## Executive Summary

This repository contains a production-ready AI-powered procurement automation system implementing a sophisticated multi-agent architecture for end-to-end procurement lifecycle management. The system automates demand forecasting, supplier discovery, quote collection, purchase order management, delivery verification, and quality assurance through twelve specialized agents coordinated by a central orchestrator.

**Architecture**: Event-driven multi-agent system with centralized orchestration  
**Primary Models**: Llama 3.3 70B Versatile, Llama 3.1 8B Instant, Llama 3.2 90B Vision Preview (Groq API)  
**Data Persistence**: JSON-based storage with CSV inventory management  
**Communication**: Email integration via Gmail SMTP and IMAP  
**Development Status**: Production-ready with comprehensive testing framework

---

## System Architecture

### Agent Hierarchy

The system consists of 12 specialized agents organized into functional layers:

**Orchestration Layer**
- **Agent 0 (Master Orchestrator)**: Central coordinator managing user interactions, intent classification, state management, and workflow routing

**Analysis Layer**
- **Agent 1 (Data Harmonizer & Forecaster)**: Three-stage pipeline for schema detection, data cleaning, and multi-model demand forecasting
- **Agent 2 (Stock Monitor)**: Real-time inventory tracking and reorder point monitoring
- **Agent 3 (Replenishment Advisor)**: Optimal order quantity calculation with safety stock and lead time considerations

**Procurement Layer**
- **Agent 4 (Supplier Discovery)**: Web-based supplier research with quality scoring
- **Agent 5 (RFQ Generator)**: Professional RFQ email composition and distribution
- **Agent 6 (Decision Agent)**: Quote collection, weighted comparison, and purchase order recommendation

**Operations Layer**
- **Agent 7 (Communication Orchestrator)**: Stakeholder notifications with rate limiting and batching
- **Agent 8 (Document Verification)**: Vision-based OCR and three-way matching verification
- **Agent 9 (Exception Handler)**: Intelligent mismatch analysis and automated decision-making
- **Agent 10 (Data Storage Agent)**: Comprehensive data persistence and inventory updates
- **Agent 11 (Quality Report Generator)**: PDF report generation with embedded evidence

### Data Flow Architecture

```
User Input
    ↓
Agent 0 (Intent Classification)
    ↓
┌─────────────────────────────────────┐
│  Demand Analysis Flow               │
│  Agent 3 → Agent 1 → Agent 2        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Procurement Flow                   │
│  Agent 4 → Agent 5 → Agent 6        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Verification Flow                  │
│  Agent 8 → Agent 9 → Agent 10 → 11  │
└─────────────────────────────────────┘
    ↓
Agent 7 (Stakeholder Notifications)
```

---

## Agent Specifications

### Agent 0 - Master Orchestrator

**Primary Responsibility**: Central coordination and conversation management

**Core Capabilities**:
- **Intent Classification**: 14 intent types using Llama 3.3 70B Versatile
  - `new_demand_check`, `find_suppliers_for_item`, `supplier_approval`, `rfq_intent`, `quote_submission`, `analyze_quotes`, `po_approval`, `inbox_check`, `notification_query`, `show_pending_rfqs`, `resume_rfq`, `acknowledgment`, `help`, `unclear`
- **State Management**: 6 conversation states (`idle`, `awaiting_supplier_approval`, `awaiting_rfq_approval`, `awaiting_quotes`, `quotes_collected`, `awaiting_po_approval`)
- **Context Preservation**: Maintains item details, quantities, supplier options, collected quotes, pending PO data
- **Quote Deduplication**: Removes duplicates based on supplier name, unit price, delivery days
- **RFQ Management**: Flexible workflows with filtering, saving, and resumption capabilities

**Models Used**:
- Llama 3.3 70B Versatile (temperature 0.1): Intent classification, RFQ parsing, manual quote parsing
- Llama 3.1 8B Instant (temperature 0.5): Approval question generation

**Key Methods**:
- `_classify_user_intent()`: Natural language understanding
- `_parse_rfq_intent()`: Filter extraction from user input
- `_parse_manual_quote()`: LLM-based quote extraction
- `_deduplicate_quotes()`: Duplicate removal logic
- `handle_user_input()`: Main orchestration entry point

---

### Agent 1 - Data Harmonizer and Demand Forecaster

**Primary Responsibility**: Transform messy historical data into accurate demand forecasts

**Architecture**: Three-stage pipeline

#### Agent 1A: Schema Detector
- **Purpose**: Identify column mappings in uploaded files
- **Model**: Llama 3.3 70B Versatile (temperature 0.1)
- **Input**: First 15 rows of CSV
- **Output**: JSON schema mapping (date_column, item_column, quantity_column, date_format, unit)
- **Validation**: Column existence, data types, null values, date parsing

#### Agent 1B: Data Cleaner
- **Purpose**: Standardize messy data
- **Operations**: Duplicate removal, date standardization, null interpolation, outlier detection (IQR method with 3.0 multiplier)
- **Strategy**: Relaxed outlier threshold to preserve legitimate bulk orders
- **Output**: Cleaned DataFrame with detailed report

#### Agent 1C: Demand Forecaster
- **Purpose**: Multi-model forecasting with automatic selection
- **Models Tested**:
  1. Moving Average (3-month baseline)
  2. Exponential Smoothing (Holt-Winters via statsmodels)
  3. Linear Regression (scikit-learn with time features)
- **Selection Process**: 80/20 train-test split, MAPE-based model selection
- **Features**: Month number, quarter, lag values (1-3 months), rolling averages (3-month, 6-month)
- **Trend Detection**: Linear regression classification (increasing/decreasing/stable)
- **Seasonality Detection**: Autocorrelation function (12-month lag)
- **Confidence Scoring**:
  - MAPE < 10%: 95% confidence
  - MAPE 10-15%: 85% confidence
  - MAPE 15-20%: 75% confidence
  - MAPE 20-30%: 65% confidence
  - MAPE > 30%: 50% confidence

**Output**: `DemandForecast` object with predicted_demand, confidence, model_used, historical_average, trend, seasonality_detected, confidence_intervals

**Design Philosophy**: LLMs used only for schema detection (pattern recognition strength); forecasting uses proven statistical libraries for mathematical reliability

---

### Agent 2 - Stock Monitor

**Primary Responsibility**: Inventory level monitoring and replenishment identification

**Core Capabilities**:
- Reads `current_inventory.csv`
- Compares current quantities against reorder points
- Calculates shortage amounts
- Identifies critical shortages (< 50% of reorder point)
- Provides bulk inventory analysis

**Data Structures**:
- `StockStatus`: item_code, item_name, current_quantity, reorder_point, needs_reorder, shortage_amount
- `InventoryItem`: Complete item details with unit, warehouse_location, maximum_capacity, last_updated

**Error Handling**:
- Returns structured error dictionaries
- `"item_not_found"`: Item code doesn't exist
- `"no_inventory_data"`: CSV empty/unreadable

---

### Agent 3 - Replenishment Advisor

**Primary Responsibility**: Optimal order quantity calculation

**Design Philosophy**: Pure replenishment mathematics; relies on Agent 1 for forecasts and Agent 2 for stock status

**Calculation Methodology**:
```
Base Need = Predicted Demand - Current Stock
Safety Stock = Predicted Demand × 0.2
Lead Time Demand = (Predicted Demand ÷ 30) × Delivery Lead Time
Total Quantity = Base Need + Safety Stock + Lead Time Demand
```

**Constraints**:
- Warehouse capacity check (caps at maximum_capacity)
- Minimum order quantity (100 units)

**Urgency Classification**:
- **Critical**: Stock runs out before delivery (days < lead time)
- **High**: Current quantity below reorder point
- **Medium**: < 14 days stock remaining
- **Low**: Adequate stock levels

**Natural Language Reasoning**:
- Uses Llama 3.3 70B Versatile (temperature 0.3)
- Brief mode: 4-5 line explanation
- Detailed mode: 2 paragraph justification
- Fallback: Bullet-point reasoning if LLM fails

**Output**: `OrderRecommendation` object with total_quantity, urgency_level, reasoning, forecast_data, stock_data

---

### Agent 4 - Supplier Discovery

**Primary Responsibility**: Web-based supplier research and quality assessment

**Methodology**:
1. **Web Search**: DuckDuckGo (15 results per query)
2. **URL Filtering**: Removes marketplaces, blogs, directories
3. **Website Scraping**: BeautifulSoup HTML parsing
4. **Information Extraction**: Regex patterns for emails and locations
5. **Quality Scoring**: 0-35 point system

**Quality Scoring System**:
- Website professionalism: 0-20 points (rating × 4)
- ISO certification: 5 points
- Years in business: up to 10 points (years ÷ 2, capped)
- Contact information completeness: 5 points

**Model Usage**:
- Llama 3.1 8B Instant (temperature 0.4): Email selection, location extraction
- Optimized from previous 70B model for cost-efficiency

**Output**: Sorted list of top N suppliers with quality_score, contact details, risk_level

**Backward Compatibility**: Maintains both quality_score (higher is better) and risk_level (Low/Medium/High)

---

### Agent 5 - RFQ Generator

**Primary Responsibility**: Professional RFQ email generation and distribution

**Key Features**:
- **Test Mode**: Environment variable `TEST_MODE` controls routing
  - `TEST_MODE=true`: Sends to predefined test emails
  - `TEST_MODE=false`: Sends to actual supplier contacts
- **Company Branding**: Uses `COMPANY_NAME` and `COMPANY_EMAIL` from environment
- **Content Validation**: Checks for required keywords (price, quotation, delivery)

**Validation Logic**:
1. Generate RFQ using Llama 3.3 70B Versatile (temperature 0.3)
2. Validate required keywords
3. If fails, retry once
4. If still fails, use fallback template
5. Ensures RFQ always sent

**Configuration Requirements**:
```env
COMPANY_NAME=Manufacturing Solutions Pvt Ltd
COMPANY_EMAIL=procurement@company.com
TEST_MODE=true
```

---

### Agent 6 - Decision Agent

**Primary Responsibility**: Quote collection, comparison, and purchase order recommendation

**Core Responsibilities**:

**Quote Collection**:
- Connects to Gmail inbox via IMAP
- Filters QUOTE type emails only
- Uses QuoteParser with Llama 3.3 70B Versatile
- Saves to `quotes_collected.json`

**Comparison Methodology**:
- **Weighted Scoring**:
  - Price weight: 50%
  - Delivery time weight: 30%
  - Supplier quality score weight: 20%
- **Normalization**: All factors normalized to 0-1 scale
  - Lower prices, faster delivery → higher scores
  - Higher quality scores → higher scores
  - Equal values → neutral score (0.5)

**Approval Logic**:
- `ALWAYS_REQUIRE_APPROVAL` flag (configurable)
- If true: All purchases need manual approval
- If false: Auto-approve below `APPROVAL_THRESHOLD`
- Budget check against `BUDGET_LIMIT`

**Models Used**:
- Llama 3.3 70B Versatile (temperature 0.1): Quote extraction
- Llama 3.1 8B Instant (temperature 0.5): Justification text

**Data Storage**:
- `quotes_collected.json`: All quotes by supplier
- `purchase_orders.json`: Approved and rejected POs

---

### Agent 7 - Communication Orchestrator

**Primary Responsibility**: Stakeholder notifications and supplier email monitoring

**Notification Events**:
- `rfq_sent`, `quote_received`, `po_created`, `po_approved`, `po_rejected`
- `supplier_update_received`, `verification_complete`, `mismatch_email_to_supplier`, `final_report`

**Rate Limiting**:
- 5-minute cooldown between similar notifications
- High-priority events bypass rate limiting
- Prevents notification spam

**Batching Mechanism**:
- Quote notifications batched within 10-minute window
- Multiple quotes sent as single summary
- Reduces stakeholder fatigue

**Data Storage**:
- `notification_logs.json`: Complete history
- `stakeholder_contacts.json`: Email addresses

---

### Agent 8 - Document Verification Agent

**Primary Responsibility**: Automated document processing and three-way matching verification

**Vision Processing**:
- Converts delivery notes and invoices to base64 JPEG
- Uses Llama 3.2 90B Vision Preview (temperature 0.1) for OCR
- Prompts for structured JSON output
- Extracts: item details, quantities, prices, supplier info, document numbers, dates, payment terms, tax

**Three-Way Matching Logic**:
Compares:
1. Purchase Order (from `purchase_orders.json`)
2. Delivery Note (extracted via vision)
3. Invoice (extracted via vision)

**Verification Checks**:
- Item code consistency
- Quantity matching (ordered vs delivered vs invoiced)
- Unit price validation (0.01 tolerance)
- Total amount verification (1.00 rupee tolerance)

**Match Status**:
- **PASS**: Zero mismatches
- **FAIL**: One or more mismatches

**Immediate Actions**:
- Sends `verification_complete` alert via Agent 7
- Alert includes match result, mismatch count, discrepancies

**Output**: Complete verification result with match_status, detailed_mismatches, extracted_data, po_data, timestamp

---

### Agent 9 - Exception Handler

**Primary Responsibility**: Intelligent mismatch analysis and automated decision-making

**Decision Thresholds**:
- Accept threshold: < 2% discrepancy
- Reject threshold: > 10% discrepancy
- Middle range: Escalate to human

**Financial Impact Calculation**:
- **Quantity Mismatches**: |Ordered - Received| × Unit Price
- **Price Mismatches**: |Invoiced - PO Price| × Quantity
- **Total Amount Mismatches**: |Invoiced Total - PO Total|

**Supplier Reputation System**:
Tracks in `supplier_history.json`:
- Total orders per supplier
- Total mismatch incidents
- Last 10 incidents with details
- Calculated mismatch rate
- **Repeat Offender Criteria**: 3+ mismatch incidents

**Automated Decision Rules**:

1. **Accept with Deduction**:
   - Discrepancy < 2% AND Not repeat offender
   - Escalation: `auto_resolve`
   - Payment deducted by financial impact

2. **Reject Shipment**:
   - Discrepancy > 10% OR Repeat offender flagged
   - Escalation: `needs_human_approval`
   - Supplier contacted for explanation

3. **Escalate to Manager**:
   - Discrepancy 2-10% AND Clean supplier history
   - Escalation: `needs_human_approval`
   - Human decision required

**Model Usage**:
- Llama 3.3 70B Versatile (temperature 0.3): Explanation generation
- Llama 3.3 70B Versatile (temperature 0.4): Supplier email drafting

**Supplier Communication**:
- Auto-sends for `accept_with_deduction` and `reject_shipment`
- Routes through Agent 7 using `mismatch_email_to_supplier` event
- `escalate_to_manager` awaits human review

---

### Agent 10 - Data Storage Agent

**Primary Responsibility**: Comprehensive data persistence and inventory management

**Data Storage Operations**:

1. **Goods Receipt Creation**:
   - Format: `GR-{PO_NUMBER}-{TIMESTAMP}`
   - Records ordered vs received quantities
   - Captures verification status and mismatches
   - Includes exception action and financial impact
   - Saves to `goods_receipts.json`

2. **Inventory Update**:
   - Loads `current_inventory.json`
   - Finds item by item_code
   - Increments current_stock by received quantity
   - Updates last_updated timestamp
   - Returns new stock level

3. **Payment Record Creation**:
   - Format: `PAY-{PO_NUMBER}-{TIMESTAMP}`
   - Calculates base amount from PO total
   - Applies deduction if `accept_with_deduction`
   - Computes final payment amount
   - Extracts payment terms (Net 30, Net 45)
   - Calculates due date
   - Sets status as `pending`
   - Saves to `payments_due.json`

4. **Document Archival**:
   - Creates PO-specific folder in `data/documents`
   - Copies delivery note with standardized naming
   - Copies invoice with standardized naming
   - Returns saved file paths

**Payment Terms Parsing**:
- Extracts numeric days from terms
- Defaults to 30 days if parsing fails
- Adds days to current date for due date

**Execute Method**: Orchestrates all four operations, returns comprehensive result with all IDs, confirmations, status

**Data Files Managed**:
- `goods_receipts.json`
- `current_inventory.json`
- `payments_due.json`
- `documents/{PO_NUMBER}/`

---

### Agent 11 - Quality Report Generator

**Primary Responsibility**: Comprehensive PDF report generation for procurement delivery cycle

**Report Generation Workflow**:

1. **Executive Summary**:
   - Uses Llama 3.3 70B Versatile (temperature 0.3)
   - Analyzes PO data and verification results
   - Generates 2-3 sentence professional summary

2. **Findings Section**:
   - Uses Llama 3.3 70B Versatile (temperature 0.3)
   - Detailed 2-3 paragraph analysis
   - Explains verification process and results
   - Specifies discrepancies and actions taken

**HTML Template Structure**:
- Header: Report title, timestamp, PO number
- Executive Summary: LLM-generated overview
- Purchase Order Details: Structured table
- Verification Results: Match status with color coding, three-way comparison table
- Exception Analysis: Recommended action, financial impact, supplier reputation, LLM explanation
- Findings and Recommendations: LLM detailed analysis
- Data Storage Summary: GR ID, inventory update, payment record, document status
- Document Evidence: Embedded delivery note and invoice images (base64)

**Image Embedding**:
- Reads image files as binary
- Encodes to base64 string
- Creates data URI: `data:image/jpeg;base64,{encoded_data}`
- Embeds directly in HTML for self-contained PDF

**PDF Generation**:
- Technology: WeasyPrint library
- Professional CSS styling
- Color-coded status (green PASS, red FAIL)
- Responsive table layouts
- File naming: `{PO_NUMBER}_delivery_report.pdf`
- Saved to `data/reports/`

**Stakeholder Notification**:
- Sends `final_report` event via Agent 7
- Includes PO details, verification status
- Attaches PDF report to email

---

## Shared Utilities

### Email Monitor (`utils/email_monitor.py`)

**Purpose**: Unified email classification for Agent 6 and Agent 7

**Classification Logic**:
- Uses Llama 3.1 8B Instant (temperature 0.1)
- Classifies as:
  - **QUOTE**: Contains pricing, unit price, delivery timeline, payment terms
  - **UPDATE**: Delivery delays, confirmations, shipping updates, inquiries

**Deduplication**:
- Each email assigned unique identifier
- Stored in `processed_emails.json`
- Prevents duplicate processing

---

### Quote Parser (`utils/quote_parser.py`)

**Purpose**: Extract structured quote data from unstructured email and PDF

**Extraction Approach**:
1. Pre-extract quantity using regex
2. Send content to LLM with quantity hint
3. LLM extracts: supplier, unit price, delivery days, payment terms, certifications
4. Validate required fields
5. Calculate missing fields if possible

**Model**: Llama 3.3 70B Versatile (temperature 0.1)

**Fallback**: Returns `parsing_status: manual_review_needed` with error message

---

### Notification Manager (`utils/notification_manager.py`)

**Purpose**: Email delivery system for stakeholder notifications

**Implementation**:
- SMTP via Gmail for outbound
- Template Manager for dynamic content
- Persistent logging to `notification_logs.json`

**Template System**:
- Event-specific subject lines and bodies
- Dynamic data insertion
- Professional formatting

---

### Email Helper (`utils/email_helper.py`)

**Purpose**: Gmail SMTP wrapper for RFQ distribution

**Features**:
- Email validation using RFC 5322 regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- Bulk sending with success/failure tracking
- Credential management via environment variables

---

### GROQ Helper (`utils/groq_helper.py`)

**Purpose**: Centralized Groq API client management

**Features**:
- Singleton pattern for client reuse
- Model configuration constants
- Error handling and retry logic
- Rate limit management

**Model Constants**:
```python
GROQ_MODELS = {
    "reasoning": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant",
    "vision": "llama-3.2-90b-vision-preview"
}
```

---

### Logger (`utils/logger.py`)

**Purpose**: Structured logging system

**Features**:
- Separate info and error logs
- Timestamp-based log rotation
- Formatted output with module context
- Log levels: INFO, ERROR, DEBUG

**Log Files**:
- `logs/info.log`: General operations
- `logs/error.log`: Errors and exceptions

---

## Data Persistence Architecture

### JSON Files

| File | Purpose | Created By | Read By |
|------|---------|------------|---------|
| `purchase_orders.json` | Approved purchase orders | Agent 6 | Agent 8, 10, 11 |
| `quotes_collected.json` | All received supplier quotes | Agent 6 | Agent 0, 6 |
| `pending_rfqs.json` | Saved RFQ drafts | Agent 0 | Agent 0 |
| `notification_logs.json` | Complete notification history | Agent 7 | Agent 0, 7 |
| `stakeholder_contacts.json` | Email addresses for notifications | Manual config | Agent 7 |
| `processed_emails.json` | Email deduplication | EmailMonitor | EmailMonitor |
| `supplier_history.json` | Supplier reliability tracking | Agent 9 | Agent 9 |
| `goods_receipts.json` | Complete delivery audit trail | Agent 10 | Agent 11 |
| `payments_due.json` | Accounts payable tracking | Agent 10 | Finance team |

### CSV Files

| File | Purpose | Format | Updated By | Read By |
|------|---------|--------|------------|---------|
| `current_inventory.csv` | Real-time stock levels | item_code, item_name, current_quantity, reorder_point, maximum_capacity, unit, warehouse_location, last_updated | Agent 10 | Agent 2, 3 |
| `historical_orders.csv` | Order history for forecasting | Flexible schema (date, item, quantity columns) | Manual export | Agent 1A, 1B, 1C |

### File System Structure

```
data/
├── current_inventory.csv
├── historical_orders.csv
├── purchase_orders.json
├── quotes_collected.json
├── pending_rfqs.json
├── notification_logs.json
├── stakeholder_contacts.json
├── processed_emails.json
├── supplier_history.json
├── goods_receipts.json
├── payments_due.json
├── documents/
│   └── {PO_NUMBER}/
│       ├── {PO_NUMBER}_delivery_note.jpg
│       └── {PO_NUMBER}_invoice.jpg
└── reports/
    └── {PO_NUMBER}_delivery_report.pdf
```

---

## Model Usage Summary

### Llama 3.3 70B Versatile (Groq API)

**Used for complex reasoning tasks**:
- Agent 0: Intent classification (14 types), RFQ parsing, manual quote parsing
- Agent 1A: Schema detection from messy columns
- Agent 3: Natural language reasoning generation
- Agent 5: Professional RFQ email composition
- Agent 6: Quote extraction from emails
- Agent 9: Exception explanation generation, supplier email drafting
- Agent 11: Executive summary generation, findings section generation
- QuoteParser: Structured data extraction

**Temperature Settings**:
- 0.1: Intent classification, quote parsing, schema detection (factual accuracy)
- 0.3: Replenishment reasoning, exception explanations, report summaries (balanced)
- 0.4: Supplier emails (diplomatic tone)
- 0.5: RFQ composition (creative but professional)

### Llama 3.1 8B Instant (Groq API)

**Used for simple, fast tasks**:
- Agent 0: Approval question generation
- Agent 4: Email selection, location extraction, supplier data extraction
- Agent 6: Justification text generation
- EmailMonitor: Binary classification (QUOTE vs UPDATE)

**Temperature Settings**:
- 0.1: Email classification (consistency)
- 0.4: Data extraction (balanced)
- 0.5: Question generation (variation)

### Llama 3.2 90B Vision Preview (Groq API)

**Used for computer vision**:
- Agent 8: Delivery note OCR and data extraction
- Agent 8: Invoice OCR and data extraction

**Temperature Settings**:
- 0.1: Document extraction (maximum accuracy for numbers and text)

### Model Selection Rationale

**70B for**: Complex multi-step reasoning, creative professional writing, ambiguous input interpretation, structured data extraction from unstructured text

**8B for**: Simple binary classification, pattern matching, template filling, speed-critical operations

**Vision 90B for**: Optical character recognition, document understanding, image-to-text conversion

---

## Environment Configuration

### Required Environment Variables

```env
# LLM API
GROQ_API_KEY=your_groq_api_key

# Email Configuration
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Company Configuration
COMPANY_NAME=Manufacturing Solutions Pvt Ltd
COMPANY_EMAIL=procurement@company.com

# Testing
TEST_MODE=true

# Agent 6 Configuration
ALWAYS_REQUIRE_APPROVAL=true
APPROVAL_THRESHOLD=50000
BUDGET_LIMIT=100000
```

### Setup Instructions

1. Create `.env` file in project root
2. Add all required environment variables
3. Ensure Gmail App Password is generated (not regular password)
4. Set `TEST_MODE=true` for development, `false` for production

---

## Testing Framework

### Test Organization

```
tests/
├── run_validation_chunk.py       # Chunked validation script
├── merge_validation_results.py   # Results aggregation
├── generate_test_data_simple.py  # Test data generator
└── comprehensive_system_validation.py  # Full system test (deprecated)
```

### Validation Strategy

**Chunked Testing Approach**:
- Tests split into small batches to avoid GROQ API rate limits
- Each chunk saves incremental results
- Progress tracked in `VALIDATION_CHECKLIST.md`
- Can resume from any point

**Test Coverage**:
- **Phase 1**: Forecasting Accuracy (20 items, 4 chunks, no API calls)
- **Phase 2**: Intent Classification (101 tests, 11 chunks, 101 API calls)
- **Phase 3**: Supplier Selection (50 scenarios, 5 chunks, minimal API calls)

**Metrics Collected**:
- Forecasting: MAPE, RMSE, confidence, model selection distribution
- Intent Classification: Accuracy, precision, recall, F1-score per intent
- Supplier Selection: Optimal decision rate, cost savings
- Performance: Response times, throughput

**Running Tests**:
```bash
# Phase 1: Forecasting (fast, no rate limits)
python tests/run_validation_chunk.py --phase 1 --chunk 1

# Phase 2: Intent Classification (slow, needs 2-min waits)
python tests/run_validation_chunk.py --phase 2 --chunk 1
# WAIT 2 MINUTES
python tests/run_validation_chunk.py --phase 2 --chunk 2

# Phase 3: Supplier Selection
python tests/run_validation_chunk.py --phase 3 --chunk 1

# After all chunks complete
python tests/merge_validation_results.py
```

**Results Storage**:
- `validation_results_incremental.json`: Incremental results (auto-saved)
- `COMPREHENSIVE_VALIDATION_RESULTS.json`: Final merged results
- `VALIDATION_SUMMARY.txt`: Publication-ready summary

---

## Error Handling Patterns

### LLM Generation Failures

**Pattern**:
1. Attempt LLM generation with primary model
2. If timeout or error, retry once
3. If still fails, use fallback template or simple text
4. Log error for monitoring
5. Never crash the workflow

**Examples**:
- Agent 0: Falls back to template questions
- Agent 5: Uses fallback RFQ template
- Agent 9: Uses simple bullet-point explanation
- Agent 11: Uses basic summary text

### Data File Corruption

**Pattern**:
1. Wrap `json.load()` in try-except
2. Check for empty file content
3. Return empty dict/array on `JSONDecodeError`
4. Log corruption warning
5. Continue with empty data structure

### Missing Context Validation

**Pattern**:
1. Check required context variables exist
2. Return user-friendly error message if missing
3. Prompt user to establish context first
4. Never proceed with None values

**Examples**:
- Agent 0: Validates `last_item_code` before quote analysis
- Agent 3: Validates `item_code` before replenishment
- Agent 8: Validates PO exists before verification

### Email Processing Robustness

**Pattern**:
1. Process emails individually in loop
2. Log parse failures but continue batch
3. Return partial results if some succeed
4. IMAP connection failures return empty list
5. Never let one email failure block all

---

## Performance Benchmarks

### Response Time Targets

| Component | Target | Typical |
|-----------|--------|---------|
| Agent 1 pipeline | < 15s | 8-12s |
| Agent 4 search | < 30s | 20-25s |
| Agent 8 vision processing | < 5s per document | 3-4s |
| Complete workflow | < 2 min (excluding human approvals) | 1.5 min |

### Accuracy Targets

| Component | Target | Achieved |
|-----------|--------|----------|
| Agent 1 MAPE (fast-moving items) | < 20% | 15-21% |
| Agent 1A schema detection | > 90% | 95%+ |
| Agent 8 OCR extraction | > 95% | 97%+ |
| Agent 9 decision correctness | 100% (rule-based) | 100% |

---

## Deployment Considerations

### Production Checklist

- [ ] Set `TEST_MODE=false` in `.env`
- [ ] Configure actual supplier emails in `stakeholder_contacts.json`
- [ ] Set up production Gmail account with App Password
- [ ] Configure `APPROVAL_THRESHOLD` and `BUDGET_LIMIT` per business rules
- [ ] Set up log rotation for `logs/` directory
- [ ] Configure backup for `data/` directory
- [ ] Set up monitoring for `logs/error.log`
- [ ] Test email delivery to actual stakeholders
- [ ] Validate GROQ API quota limits
- [ ] Set up scheduled email monitoring (Agent 6 background job)

### Scaling Considerations

**Rate Limiting**:
- GROQ API: ~30 requests/minute (free tier), ~6000/minute (paid tier)
- Gmail SMTP: 500 emails/day (free), 2000/day (Google Workspace)
- Gmail IMAP: No strict limits, but avoid excessive polling

**Data Growth**:
- JSON files grow linearly with orders
- Consider archival strategy for old POs (> 1 year)
- Document images consume significant storage
- Implement periodic cleanup of old reports

**Concurrent Users**:
- Current architecture supports single-user conversation
- For multi-user, implement session management in Agent 0
- Consider database migration for high-volume scenarios

---

## Repository Structure

```
MAS/
├── agents/                          # Agent implementations
│   ├── Agent0.py                    # Master Orchestrator
│   ├── Agent1_complete.py           # Data Harmonizer & Forecaster
│   ├── Agent2_stockMonitor.py       # Stock Monitor
│   ├── Agent3_replenishmentAdvisor.py  # Replenishment Advisor
│   ├── Agent4_supplierDiscovery.py  # Supplier Discovery
│   ├── Agent5_rfqGenerator.py       # RFQ Generator
│   ├── Agent6_decisionMaker.py      # Decision Agent
│   ├── Agent7_communicationOrchestrator.py  # Communication Orchestrator
│   ├── Agent8_documentVerification.py  # Document Verification
│   ├── Agent9_exceptionHandler.py   # Exception Handler
│   ├── Agent10_dataStorage.py       # Data Storage Agent
│   ├── Agent11_qualityReportGenerator.py  # Quality Report Generator
│   └── base_agent.py                # Base agent class
├── utils/                           # Shared utilities
│   ├── email_monitor.py             # Email classification
│   ├── quote_parser.py              # Quote extraction
│   ├── notification_manager.py      # Notification system
│   ├── email_helper.py              # SMTP wrapper
│   ├── groq_helper.py               # Groq API client
│   └── logger.py                    # Logging system
├── config/                          # Configuration
│   └── settings.py                  # System settings
├── models/                          # Data models
│   └── data_models.py               # Dataclass definitions
├── data/                            # Data storage
│   ├── current_inventory.csv
│   ├── historical_orders.csv
│   ├── purchase_orders.json
│   ├── quotes_collected.json
│   ├── pending_rfqs.json
│   ├── notification_logs.json
│   ├── stakeholder_contacts.json
│   ├── processed_emails.json
│   ├── supplier_history.json
│   ├── goods_receipts.json
│   ├── payments_due.json
│   ├── documents/
│   └── reports/
├── logs/                            # System logs
│   ├── info.log
│   └── error.log
├── tests/                           # Testing framework
│   ├── run_validation_chunk.py
│   ├── merge_validation_results.py
│   └── generate_test_data_simple.py
├── docs/                            # Documentation
│   ├── CHUNKED_VALIDATION_GUIDE.md
│   ├── VALIDATION_PROGRESS_REPORT.md
│   └── READY_TO_START.md
├── .env                             # Environment variables (not in git)
├── .gitignore
├── README.md                        # This file
├── VALIDATION_CHECKLIST.md          # Testing progress tracker
├── CHANGE_AND_VALIDATION_REPORT.md  # Validation results
└── EVALUATION_AND_METRICS_REPORT.md # Research metrics
```

---

## License

Proprietary - All Rights Reserved

---

## Contact

For questions or support, contact the development team.

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-01  
**Status**: Production-Ready
