# Multi-Agent Procurement System

An AI-powered procurement automation system that manages the full purchasing lifecycle — from detecting low stock and forecasting demand, to sourcing suppliers, collecting quotes, issuing purchase orders, and verifying deliveries — with minimal human intervention.

Built for manufacturing and operations teams who manage procurement across spreadsheets, inboxes, and manual approvals.

---

## The Problem

Procurement is fragmented by nature. Someone notices stock is low, emails a few suppliers, waits on quotes, forwards them to a manager for approval, raises a PO, and then hopes the delivery matches what was ordered. Each step is manual, slow, and error-prone — and mistakes at any stage ripple through the entire supply chain.

This system automates the entire chain. You interact with it conversationally, approve what matters, and it handles the rest.

---

## What It Does

**Inventory & Demand Analysis**
The system monitors your inventory in real time and flags items approaching reorder thresholds. When replenishment is needed, it analyzes your historical order data to forecast demand and calculate exactly how much to order — accounting for safety stock, lead times, and warehouse capacity.

**Supplier Discovery**
Rather than relying on a static vendor list, the system searches the web for qualified suppliers for any item, evaluates them on professionalism, certifications, and reliability, and presents a ranked shortlist for your approval.

**RFQ Distribution**
Once you approve a supplier list, the system drafts professional Request for Quotation emails tailored to each supplier and sends them directly from your company email. No copy-pasting, no manual follow-up.

**Quote Collection & Comparison**
Supplier quotes that arrive in your inbox are automatically read, parsed, and compared. The system scores each quote on price, delivery time, and supplier quality, then recommends the best option with a clear justification — ready for your sign-off.

**Purchase Order Management**
Approved quotes become purchase orders automatically. The system tracks pending POs, manages approval workflows, and keeps stakeholders notified at every step.

**Delivery Verification**
When goods arrive, the system reads the delivery note and invoice using computer vision and performs a three-way match against the original purchase order. Discrepancies are caught automatically — minor variances are resolved with payment adjustments, significant ones are escalated or rejected with supplier communication handled for you.

**Audit Trail & Reporting**
Every completed delivery cycle produces a structured PDF report covering the full procurement-to-delivery record, including verification results, any exceptions, and the actions taken.

---

## How You Interact With It

The system is conversational. You tell it what you need in plain language:

> *"Check stock levels for item A-204"*  
> *"Find suppliers for industrial ball bearings"*  
> *"Send RFQs to the top 3 suppliers"*  
> *"Show me the quotes that came in"*  
> *"Approve the PO for Supplier B"*  

It understands your intent, maintains context across the conversation, and picks up where you left off if a workflow is interrupted.

---

## Key Design Decisions

**Humans stay in the loop where it matters.** Supplier selection, RFQ dispatch, and purchase order approval are all confirmation steps — the system presents its recommendation and waits for your go-ahead before acting.

**Automation handles the rest.** Routine tasks like reading emails, parsing quotes, matching documents, and sending notifications happen without any input needed.

**Nothing gets lost.** Every quote, order, delivery, payment record, and notification is persisted. The system can resume interrupted workflows and maintain a full audit history.

---

## Setup

**Prerequisites**
- Python 3.9+
- A Groq API key
- A Gmail account with App Password enabled

**Configuration**

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key

GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

COMPANY_NAME=Your Company Name
COMPANY_EMAIL=procurement@yourcompany.com

TEST_MODE=true
ALWAYS_REQUIRE_APPROVAL=true
APPROVAL_THRESHOLD=50000
BUDGET_LIMIT=100000
```

Set `TEST_MODE=true` during development to route all outbound emails to test addresses. Set to `false` for production.

**Install dependencies**

```bash
pip install -r requirements.txt
```

**Run**

```bash
python main.py
```

---

## Data

The system works with two files you provide:

- `data/current_inventory.csv` — your current stock levels, reorder points, and warehouse details
- `data/historical_orders.csv` — past order history used for demand forecasting (flexible schema; the system figures out your column names automatically)

Everything else — purchase orders, quotes, receipts, payment records, reports — is generated and managed by the system.

---

## Tech Stack

- **LLMs**: Llama 3.3 70B, Llama 3.1 8B, Llama 3.2 90B Vision (via Groq API)
- **Email**: Gmail SMTP / IMAP
- **Forecasting**: statsmodels, scikit-learn
- **Document Processing**: WeasyPrint, BeautifulSoup
- **Storage**: JSON + CSV (file-based, no database required)