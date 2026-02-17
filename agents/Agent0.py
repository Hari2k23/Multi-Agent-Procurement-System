import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base_agent import BaseAgent
from agents.Agent3_replenishmentAdvisor import ReplenishmentAdvisor
from agents.Agent4_supplierDiscovery import SupplierDiscovery
from agents.Agent5_rfqGenerator import RFQGenerator
from agents.Agent6_decisionMaker import DecisionAgent
from agents.Agent7_communicationOrchestrator import CommunicationOrchestrator
from utils.groq_helper import groq
from utils.logger import log_info, log_error
import json
import re
from datetime import datetime
import pandas as pd             # type: ignore


class MasterOrchestrator(BaseAgent):
    """Intent-based flow coordinator that routes requests to appropriate agents."""
    def __init__(self):
        super().__init__(
            name="Agent 0 - Master Orchestrator",
            role="Procurement Flow Coordinator",
            goal="Route user requests to appropriate agents and manage conversation flow",
            backstory="Expert in understanding user intent and orchestrating multi-agent workflows"
        )
        log_info("Master Orchestrator initialized", self.name)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.advisor = ReplenishmentAdvisor()
        self.supplier_finder = SupplierDiscovery()
        self.rfq_generator = RFQGenerator()
        self.decision_agent = DecisionAgent()
        self.communication_agent = CommunicationOrchestrator()
        self.state = "idle"
        self.last_item_code = None
        self.last_item_name = None
        self.last_quantity = None
        self.last_suppliers = None
        self.rfq_sent = False
        self.collected_quotes = []
        self.pending_po_data = None
       
        self.pending_rfqs_file = os.path.join(project_root, 'data', 'pending_rfqs.json')

    def process_request(self, user_input: str) -> str:
        """Process user request by classifying intent and routing to appropriate handler."""
        log_info(f"Processing: {user_input}", self.name)
       
        intent = self._classify_user_intent(user_input)
        log_info(f"Detected intent: {intent['type']}", self.name)
       
        if intent['type'] == 'new_demand_check':
            self._reset_state()
            return self._handle_demand_check(user_input)
       
        elif intent['type'] == 'find_suppliers_for_item':
            item_name = intent.get('item_name')
            return self._handle_supplier_request(user_input, item_name)
       
        elif intent['type'] == 'show_pending_rfqs':
            return self._show_pending_rfqs()
       
        elif intent['type'] == 'resume_rfq':
            item_identifier = intent.get('item_identifier')
            if not item_identifier:
                return "I have pending RFQs saved. Could you tell me which one you'd like to continue? You can mention the item name, item code, or when you created it."
            return self._resume_rfq(item_identifier)
       
        elif intent['type'] == 'help':
            return self._show_help()
       
        elif intent['type'] == 'supplier_approval':
            if self.state == "awaiting_supplier_approval":
                if intent.get('response') == 'yes':
                    return self._find_suppliers()
                else:
                    self._reset_state()
                    return "Alright, no problem. Just let me know when you need something."
            else:
                return "I'm not sure what you're referring to. Would you like to check an item's inventory status?"
       
        elif intent['type'] == 'rfq_intent':
            if self.state == "awaiting_rfq_approval":
                return self._handle_rfq_intent(user_input, intent)
            else:
                return "I'm not currently waiting for RFQ instructions. Would you like to check an item's status?"
       
        elif intent['type'] == 'quote_submission':
            return self._handle_quote_submission(user_input)
       
        elif intent['type'] == 'analyze_quotes':
            return self._handle_analyze_quotes()
       
        elif intent['type'] == 'po_approval':
            if self.state == "awaiting_po_approval":
                return self._handle_po_approval(intent)
            else:
                return "I'm not currently waiting for PO approval. Would you like to check an item's status?"
       
        elif intent['type'] == 'notification_query':
            return self._handle_notification_query(user_input)
       
        elif intent['type'] == 'inbox_check':
            return self._handle_inbox_check(user_input)
       
        elif intent['type'] == 'acknowledgment':
            return self._handle_acknowledgment()
       
        elif intent['type'] == 'unclear':
            return self._handle_unclear_intent()
       
        else:
            return "I didn't understand that. Type 'help' to see what I can do."

    def _classify_user_intent(self, user_input: str) -> dict:
        """Use LLM to classify user intent from natural language."""
       
        prompt = f"""You are analyzing user input in a procurement conversation system. Classify the user's intent.
Current conversation state: {self.state}
Current item being discussed: {self.last_item_name if self.last_item_name else "None"}
User said: "{user_input}"
Classify into ONE of these intents and return ONLY a JSON object:
1. "new_demand_check" - User wants to check inventory/order status for an item
   Examples: "check M8 screws", "status of electric motors", "do we need bearings"
   Return: {{"type": "new_demand_check"}}
2. "find_suppliers_for_item" - User explicitly asks to find/get suppliers for a SPECIFIC item
   Examples: "get suppliers for M8 screws", "find suppliers for electric motors"
   Return: {{"type": "find_suppliers_for_item", "item_name": "extracted item name"}}
3. "show_pending_rfqs" - User wants to see saved/pending RFQs
   Examples: "show pending rfqs", "list saved orders"
   Return: {{"type": "show_pending_rfqs"}}
4. "resume_rfq" - User wants to continue a saved RFQ
   Examples: "continue M8 screws RFQ", "resume bearings order"
   Return: {{"type": "resume_rfq", "item_identifier": "item name or code or date reference"}}
5. "supplier_approval" - User responding yes/no to supplier search question
   Examples: "yes", "yeah", "sure", "no", "nope", "not now"
   Return: {{"type": "supplier_approval", "response": "yes" or "no"}}
6. "rfq_intent" - User responding to RFQ approval (send/wait/cancel with filters)
   Examples: "yes send to all", "only low risk", "wait for now"
   Return: {{"type": "rfq_intent"}}
7. "quote_submission" - User submitting quotes OR informing about received quotes (NOT analyzing)
   Examples: "received quotes", "I got a quote from supplier", pasting quote text with pricing details
   Return: {{"type": "quote_submission"}}
8. "analyze_quotes" - User wants to ANALYZE/COMPARE collected quotes NOW
   Examples: "analyze quotes", "compare quotes", "done", "ready to compare", "analyse quotes", "let's see", "what do we have", "show me the quotes"
   Return: {{"type": "analyze_quotes"}}
9. "po_approval" - User responding to purchase order approval question
   Examples: "yes approve", "no reject", "confirm", "proceed"
   Return: {{"type": "po_approval", "response": "yes" or "no"}}
10. "notification_query" - User asking about sent notifications or notification history
    Examples: "what notifications did you send", "show recent alerts", "notification history"
    Return: {{"type": "notification_query"}}
11. "inbox_check" - User asking to check inbox or about supplier emails
    Examples: "check inbox", "any mails from suppliers", "did we get quotes", "any new emails"
    Return: {{"type": "inbox_check"}}
12. "acknowledgment" - User providing simple acknowledgment or casual response
    Examples: "okay", "ok", "alright", "got it", "thanks"
    Return: {{"type": "acknowledgment"}}
13. "help" - User asking for help or guidance
    Examples: "help", "what can you do"
    Return: {{"type": "help"}}
14. "unclear" - Cannot determine intent
    Return: {{"type": "unclear"}}
CRITICAL RULES:
- "analyze", "analyse", "compare", "done", "let's see", "what do we have", "ready", "show me" (when talking about quotes) → ALWAYS "analyze_quotes"
- "I got quote" (informing) → "quote_submission"
- Pasting quote data with prices → "quote_submission"
- "check inbox" → "inbox_check"
- Simple "ok", "thanks" → "acknowledgment"
Return ONLY the JSON object, no explanation."""
        try:
            response = groq.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
           
            result_text = response.choices[0].message.content.strip()
           
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
           
            intent = json.loads(result_text)
            return intent
           
        except Exception as e:
            log_error(f"Intent classification failed: {e}", self.name)
            return {"type": "unclear"}

    def _handle_demand_check(self, user_input: str) -> str:
        """Handle new demand check request."""
       
        item_code = self._extract_item(user_input)
        if not item_code:
            return "I couldn't identify the item. Try like: 'Status of M8 Screws' or 'Check Electric Motors'."
        log_info(f"Checking order for {item_code}", self.name)
        result = self.advisor.execute(item_code, forecast_days=30)
        if not result:
            return "Item not found in inventory database."
       
        # Check if result contains error
        if result.get('error'):
            return f"Error: {result.get('message', 'Unknown error occurred')}"
        rec = result['recommendation']
        self.last_item_code = item_code
        self.last_item_name = rec.item_name
        self.last_quantity = rec.recommended_quantity
        self.state = "awaiting_supplier_approval"
        
        return f"""### Inventory Analysis: {rec.item_name}
**Primary Recommendation**: Procure **{rec.recommended_quantity} units**
**Urgency Level**: {rec.urgency}

**Justification**:
{rec.reason}

---
{self._generate_supplier_approval_question()}"""

    def _handle_supplier_request(self, user_input: str, suggested_item_name: str = None) -> str:
        """Handle explicit supplier search request for a specific item."""
       
        if suggested_item_name:
            item_code = self._extract_item(suggested_item_name)
        else:
            item_code = self._extract_item(user_input)
       
        if not item_code:
            return "I couldn't identify which item you want suppliers for. Could you specify the item name?"
       
        log_info(f"Running demand analysis for {item_code} before supplier search", self.name)
        result = self.advisor.execute(item_code, forecast_days=30)
       
        if not result:
            return "Item not found in inventory database."
       
        # Check if result contains error
        if result.get('error'):
            return f"Error: {result.get('message', 'Unknown error occurred')}"
       
        rec = result['recommendation']
       
        self.last_item_code = item_code
        self.last_item_name = rec.item_name
        self.last_quantity = rec.recommended_quantity
       
        log_info(f"Proceeding directly to supplier search for {self.last_item_name}", self.name)
        return self._find_suppliers()

    def _generate_supplier_approval_question(self) -> str:
        """Generate varied, natural supplier approval questions."""
        import random
       
        questions = [
            "Would you like me to suggest suppliers for this item?",
            "Should I look for suppliers for this?",
            "Want me to find some supplier options?",
            "Shall I search for suppliers who can fulfill this order?",
            "Would you like to see supplier recommendations?",
            "Should I find suppliers for this item?",
            "Do you want me to search for available suppliers?",
        ]
       
        return random.choice(questions)
   
    def _find_suppliers(self) -> str:
        log_info(f"Finding suppliers for {self.last_item_code}", self.name)
        supplier_result = self.supplier_finder.execute(
            self.last_item_code,
            self.last_item_name,
            top_n=5
        )
        if not supplier_result or not supplier_result.get('suppliers'):
            return "No suppliers found for this item."
        self.last_suppliers = supplier_result
        suppliers_text = self.supplier_finder.format_supplier_info(supplier_result['suppliers'])
        self.state = "awaiting_rfq_approval"
        approval_question = self._generate_rfq_approval_question()
        
        return f"""### Supplier Identification: {self.last_item_name}
{suppliers_text}

---
**Verification**: {approval_question}"""

    def _generate_rfq_approval_question(self) -> str:
        """Generate natural language approval question using LLM."""
        prompt = f"""Generate a natural, friendly question asking if the user wants to send RFQs to suppliers.
Context:
- Item: {self.last_item_name}
- Recommended quantity: {self.last_quantity} units
- Default delivery: 14 days
Requirements:
- Mention the recommended quantity naturally
- Mention default delivery timeline
- Invite user to specify different quantity/delivery if needed
- Sound conversational, not robotic
- Be 1-2 sentences maximum
- Return ONLY the question text with NO quotes, NO markdown formatting, NO special characters
Generate ONLY the question text, nothing else. No quotes. No markdown."""
        try:
            response = groq.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100
            )
           
            question = response.choices[0].message.content.strip()
            question = question.strip('"').strip("'").strip('`')
           
            return question
           
        except Exception as e:
            log_error(f"Question generation failed: {e}", self.name)
            return f"Based on our analysis, we'd need {self.last_quantity} units with 14-day delivery. Would you like to send RFQs to these suppliers?"

    def _handle_rfq_intent(self, user_input: str, classified_intent: dict) -> str:
        """Classify user's natural language intent for RFQ using LLM."""
       
        log_info("Classifying user RFQ intent...", self.name)
       
        supplier_list_text = ""
        for i, sup in enumerate(self.last_suppliers['suppliers'], 1):
            # Handle both risk_level and quality_level for backward compatibility
            quality_or_risk = sup.get('quality_level', sup.get('risk_level', 'Unknown'))
            supplier_list_text += f"{i}. {sup['supplier_name']} - {sup['location']} - {quality_or_risk} - {sup['contact_email']}\n"
       
        prompt = f"""Analyze the user's response and classify their intent for sending RFQs.
User said: "{user_input}"
Context:
- Item: {self.last_item_name}
- Recommended quantity: {self.last_quantity} units
- Default delivery days: 14
Available suppliers:
{supplier_list_text}
Classify the user's intent and return ONLY a JSON object:
{{
  "action": "send" or "wait" or "cancel",
  "quantity": {self.last_quantity} or user's modified quantity,
  "delivery_days": 14 or user's specified days (convert "urgent" to 7, "fast" to 5, etc.),
  "filter_type": "all" or "risk_based" or "count_based" or "name_based" or "location_based",
  "filter_value": appropriate value based on filter_type
}}
Rules:
- action "send" means proceed with RFQs
- action "wait" means save for later
- action "cancel" means stop the process
- filter_type "all" → filter_value: "all"
- filter_type "risk_based" → filter_value: ["Low Risk"] or ["Low Risk", "Medium Risk"] (also accept "High Quality", "Medium Quality")
- filter_type "count_based" → filter_value: number (e.g., 3 for "first 3")
- filter_type "name_based" → filter_value: list of supplier names (fuzzy match)
- filter_type "location_based" → filter_value: list of locations
Examples:
"yes" → {{"action": "send", "quantity": {self.last_quantity}, "delivery_days": 14, "filter_type": "all", "filter_value": "all"}}
"send to low risk only" → {{"action": "send", "quantity": {self.last_quantity}, "delivery_days": 14, "filter_type": "risk_based", "filter_value": ["Low Risk"]}}
"first 3 suppliers, 7 days delivery" → {{"action": "send", "quantity": {self.last_quantity}, "delivery_days": 7, "filter_type": "count_based", "filter_value": 3}}
"wait for now" → {{"action": "wait", "quantity": {self.last_quantity}, "delivery_days": 14, "filter_type": null, "filter_value": null}}
Return ONLY the JSON, no explanation."""
        try:
            response = groq.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
           
            result_text = response.choices[0].message.content.strip()
           
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
           
            intent = json.loads(result_text)
            log_info(f"RFQ Intent classified: {intent}", self.name)
           
            if intent['action'] == 'send':
                return self._send_rfqs_with_filters(intent)
            elif intent['action'] == 'wait':
                return self._save_pending_rfq(intent)
            elif intent['action'] == 'cancel':
                self._reset_state()
                return "Alright, no worries. Let me know when you're ready to proceed."
           
        except Exception as e:
            log_error(f"RFQ intent classification failed: {e}", self.name)
            return "I couldn't understand your request. Could you please rephrase? (e.g., 'yes, send to all' or 'only low risk suppliers')"

    def _send_rfqs_with_filters(self, intent: dict) -> str:
        """Send RFQs to filtered suppliers based on intent."""
       
        all_suppliers = self.last_suppliers['suppliers']
        selected_suppliers = []
       
        filter_type = intent.get('filter_type')
        filter_value = intent.get('filter_value')
       
        if filter_type == "all":
            selected_suppliers = all_suppliers
       
        elif filter_type == "risk_based":
            # Support both risk_level and quality_level filtering
            selected_suppliers = [
                s for s in all_suppliers
                if s.get('risk_level') in filter_value or s.get('quality_level') in filter_value
            ]
       
        elif filter_type == "count_based":
            selected_suppliers = all_suppliers[:filter_value]
       
        elif filter_type == "name_based":
            selected_suppliers = [s for s in all_suppliers if s['supplier_name'] in filter_value]
       
        elif filter_type == "location_based":
            selected_suppliers = [s for s in all_suppliers if s['location'] in filter_value]
       
        else:
            selected_suppliers = all_suppliers
       
        if not selected_suppliers:
            return "No suppliers match your criteria. Please try different filters."
       
        log_info(f"Filtered to {len(selected_suppliers)} suppliers", self.name)
       
        quantity = intent.get('quantity', self.last_quantity)
        delivery_days = intent.get('delivery_days', 14)
       
        rfq_result = self.rfq_generator.execute(
            self.last_item_code,
            self.last_item_name,
            quantity,
            selected_suppliers,
            delivery_days=delivery_days
        )
        if not rfq_result:
            self._reset_state()
            return "RFQ sending failed. Check email configuration."
        self.rfq_sent = True
        self.state = "awaiting_quotes"
        self.communication_agent.send_notification('rfq_sent', {
            'item_name': self.last_item_name,
            'quantity': quantity,
            'suppliers_contacted': rfq_result['suppliers_contacted'],
            'emails_sent': rfq_result['emails_sent'],
            'success_list': rfq_result['success_list'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        sent = "\n".join([f"- {e}" for e in rfq_result['success_list']])
        return f"""RFQs sent successfully
Details:
- Item: {self.last_item_name}
- Quantity: {quantity} units
- Delivery Timeline: {delivery_days} days
- Suppliers Contacted: {rfq_result['suppliers_contacted']}
- Emails Sent: {rfq_result['emails_sent']}/{rfq_result['suppliers_contacted']}
Delivered to:
{sent}
Stakeholders have been notified. Once you receive quotes, you can check the inbox or say "analyze quotes" when ready."""

    def _save_pending_rfq(self, intent: dict) -> str:
        """Save RFQ to pending_rfqs.json for later."""
       
        rfq_id = f"{self.last_item_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
       
        pending_rfq = {
            "rfq_id": rfq_id,
            "item_code": self.last_item_code,
            "item_name": self.last_item_name,
            "quantity": intent.get('quantity', self.last_quantity),
            "delivery_days": intent.get('delivery_days', 14),
            "suppliers": self.last_suppliers['suppliers'],
            "status": "pending",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
       
        try:
            if os.path.exists(self.pending_rfqs_file):
                with open(self.pending_rfqs_file, 'r') as f:
                    pending_rfqs = json.load(f)
            else:
                pending_rfqs = {}
        except Exception as e:
            log_error(f"Failed to load pending RFQs: {e}", self.name)
            pending_rfqs = {}
       
        pending_rfqs[rfq_id] = pending_rfq
       
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.pending_rfqs_file, 'w') as f:
                json.dump(pending_rfqs, f, indent=2)
            log_info(f"Saved pending RFQ: {rfq_id}", self.name)
        except Exception as e:
            log_error(f"Failed to save pending RFQ: {e}", self.name)
            return "Failed to save RFQ. Please try again."
       
        item_display_name = self.last_item_name if self.last_item_name else "this item"
       
        self._reset_state()
       
        return f"""RFQ saved to pending list.
You can resume this later by mentioning {item_display_name} again, or ask me to show you all pending orders whenever you're ready."""

    def _show_pending_rfqs(self) -> str:
        """Display all pending RFQs."""
       
        try:
            if not os.path.exists(self.pending_rfqs_file):
                return "No pending RFQs found. All clear!"
           
            with open(self.pending_rfqs_file, 'r') as f:
                pending_rfqs = json.load(f)
           
            if not pending_rfqs:
                return "No pending RFQs found. All clear!"
           
            output = "Pending RFQs:\n\n"
            for rfq_id, rfq in pending_rfqs.items():
                output += f"Item: {rfq['item_name']}\n"
                output += f" Quantity: {rfq['quantity']} units\n"
                output += f" Delivery: {rfq['delivery_days']} days\n"
                output += f" Suppliers Found: {len(rfq['suppliers'])}\n"
                output += f" Created: {rfq['created_at']}\n\n"
           
            output += "To resume any of these, just mention the item name and I'll help you continue."
           
            return output
           
        except Exception as e:
            log_error(f"Failed to show pending RFQs: {e}", self.name)
            return "Error loading pending RFQs."

    def _resume_rfq(self, item_identifier: str) -> str:
        """Resume a saved RFQ with fuzzy matching support."""
       
        try:
            if not os.path.exists(self.pending_rfqs_file):
                return "No pending RFQs found to resume."
           
            with open(self.pending_rfqs_file, 'r') as f:
                pending_rfqs = json.load(f)
           
            if not pending_rfqs:
                return "No pending RFQs found. All clear!"
           
            matched_rfq = None
            matched_id = None
           
            item_identifier_lower = item_identifier.lower()
            item_identifier_clean = item_identifier_lower.replace('rfq', '').replace('order', '').replace('the', '').strip()
           
            search_words = [w for w in item_identifier_clean.split() if len(w) > 2]
           
            for rfq_id, rfq in pending_rfqs.items():
                item_name_lower = rfq['item_name'].lower()
                item_code_lower = rfq['item_code'].lower()
                created_date = rfq['created_at'].split()[0]
               
                if search_words and any(word in item_name_lower for word in search_words):
                    matched_rfq = rfq
                    matched_id = rfq_id
                    break
               
                if item_code_lower[:4] in item_identifier_lower or item_identifier_lower in item_code_lower:
                    matched_rfq = rfq
                    matched_id = rfq_id
                    break
               
                if item_identifier_lower in created_date.lower():
                    matched_rfq = rfq
                    matched_id = rfq_id
                    break
               
                item_name_words = [w for w in item_name_lower.split() if len(w) > 2]
                if item_name_words and any(word in item_identifier_lower for word in item_name_words):
                    matched_rfq = rfq
                    matched_id = rfq_id
                    break
           
            if not matched_rfq:
                return f"I couldn't find a pending RFQ matching '{item_identifier}'. Would you like to see all pending orders?"
           
            self.last_item_code = matched_rfq['item_code']
            self.last_item_name = matched_rfq['item_name']
            self.last_quantity = matched_rfq['quantity']
            self.last_suppliers = {'suppliers': matched_rfq['suppliers']}
            self.state = "awaiting_rfq_approval"
           
            suppliers_text = self.supplier_finder.format_supplier_info(matched_rfq['suppliers'])
           
            return f"""Resumed pending RFQ for {matched_rfq['item_name']}
Supplier Options:
{suppliers_text}
Ready to send RFQs for {matched_rfq['quantity']} units with {matched_rfq['delivery_days']}-day delivery.
Would you like to proceed, modify the specifications, or save it for later?"""
           
        except Exception as e:
            log_error(f"Failed to resume RFQ: {e}", self.name)
            return "Error resuming RFQ."

    def _handle_quote_submission(self, user_input: str) -> str:
        """Handle both manual quote pasting and automated quote reception."""
        lower = user_input.lower()

        if any(keyword in lower for keyword in ["received quote", "got quote", "i got a", "quotation for", "quote from supplier"]):
            log_info("User mentioned received quotes, checking inbox...", self.name)

            inbox_result = self.decision_agent.check_and_parse_quotes(self.last_item_code if self.last_item_code else None)

            if inbox_result['quotes_found'] > 0:
                parsed_count = len(inbox_result['parsed_quotes'])

                # Auto-notify stakeholders via Agent 7
                for quote in inbox_result['parsed_quotes']:
                    self.communication_agent.send_notification('quote_received', {
                        'item_name': quote.get('item_name', self.last_item_name),
                        'supplier_name': quote['supplier_name'],
                        'unit_price': quote['unit_price'],
                        'delivery_days': quote['delivery_days'],
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                # Generate email summary
                summary_text = "\n\n".join([
                    f"From: {email['from']}\nSummary: {email['summary']}"
                    for email in inbox_result['emails_summary']
                ])

                # Set state to quotes_collected when quotes are found
                self.state = "quotes_collected"

                return f"""Found {inbox_result['quotes_found']} new quote email(s) from suppliers:

{summary_text}
Successfully parsed {parsed_count} quote(s). Stakeholders have been notified.
Say "analyze quotes" when ready to compare all quotes."""
            else:
                self.state = "awaiting_quotes"
                return """No new quotes found in inbox. Please paste the quote details here, and I'll process them.
Say "analyze quotes" when you've finished."""

        # Parse manual quote and normalize to standard format
        parsed_manual_quote = self._parse_manual_quote(user_input)
        if parsed_manual_quote:
            self.collected_quotes.append(parsed_manual_quote)
            self.state = "quotes_collected"
            return f"Quote {len(self.collected_quotes)} received. Paste next or say 'analyze quotes'."
        else:
            return "I couldn't parse that quote. Please include supplier name, unit price, and delivery days."

    def _parse_manual_quote(self, quote_text: str) -> dict:
        """Parse manually pasted quote into standardized dict format."""
        try:
            prompt = f"""Parse this quote text into structured JSON format.
Quote text: "{quote_text}"
Extract and return ONLY a JSON object with these fields: {{ "supplier_name": "extracted supplier name", "unit_price": numeric value only (no currency symbol), "delivery_days": numeric days, "payment_terms": "extracted payment terms or 'Not specified'", "quality_certs": "extracted certifications or 'None'", "item_name": "item name if mentioned, otherwise null", "quantity": numeric quantity if mentioned, otherwise null }}
If information is missing, use null for optional fields, 'Not specified' for payment_terms, 'None' for quality_certs. Return ONLY the JSON object."""

            response = groq.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()

            parsed = json.loads(result_text)

            # Validate required fields
            if parsed.get('supplier_name') and parsed.get('unit_price') and parsed.get('delivery_days'):
                # Add missing fields with defaults to match Agent 6 format
                parsed['risk_score'] = 0  # Default risk score
                parsed['contact_email'] = 'manual_entry'  # Mark as manually entered

                # Ensure quality_certs and payment_terms have values
                if not parsed.get('quality_certs'):
                    parsed['quality_certs'] = 'None'
                if not parsed.get('payment_terms'):
                    parsed['payment_terms'] = 'Not specified'

                return parsed
            else:
                return None

        except Exception as e:
            log_error(f"Failed to parse manual quote: {e}", self.name)
            return None

    def _handle_analyze_quotes(self) -> str:
        """Analyze all collected quotes from inbox or manual entry."""

        # Validation: Check if we have context
        if not self.last_item_code or not self.last_item_name:
            return "I don't have context for which item we're analyzing quotes for. Could you check the item status first?"

        log_info("Analyzing all collected quotes...", self.name)

        # Load quotes from quotes_collected.json
        quotes_file = self.get_data_path('quotes_collected.json')

        all_quotes = []

        # Try to load from file first
        if os.path.exists(quotes_file):
            with open(quotes_file, 'r') as f:
                quotes_data = json.load(f)

            # Extract all quotes
            for supplier_email, supplier_data in quotes_data.items():
                for quote in supplier_data['quotes']:
                    quote['contact_email'] = supplier_email
                    # Add backward compatibility for quality_score/risk_score
                    if 'risk_score' not in quote and 'quality_score' in quote:
                        quote['risk_score'] = quote['quality_score']
                    elif 'risk_score' not in quote:
                        quote['risk_score'] = 0
                    all_quotes.append(quote)

        # Add manually collected quotes
        if self.collected_quotes:
            all_quotes.extend(self.collected_quotes)

        # Deduplicate quotes
        all_quotes = self._deduplicate_quotes(all_quotes)

        if not all_quotes:
            return "No quotes available to analyze. Check inbox first or paste quotes manually."

        return self._analyze_quotes_internal(all_quotes)

    def _deduplicate_quotes(self, quotes: list) -> list:
        """Remove duplicate quotes based on supplier name, unit price, and delivery days."""
        seen = set()
        unique_quotes = []

        for quote in quotes:
            supplier = quote.get('supplier_name', '').lower().strip()
            price = quote.get('unit_price', 0)
            delivery = quote.get('delivery_days', 0)

            # Create unique key with supplier, price, AND delivery
            key = f"{supplier}_{price}_{delivery}"

            if key not in seen:
                seen.add(key)
                unique_quotes.append(quote)
            else:
                log_info(f"Removed duplicate quote: {supplier} @ Rs.{price} ({delivery} days)", self.name)

        return unique_quotes

    def _analyze_quotes_internal(self, quote_data_list) -> str:
        """Internal method to analyze quotes."""
        log_info("Running quote analysis...", self.name)

        category = self._get_item_category(self.last_item_code)

        result = self.decision_agent.execute(
            quote_data_list,
            self.last_item_code,
            self.last_item_name,
            self.last_quantity
        )

        self.collected_quotes = []

        if not result or result.get('error'):
            self._reset_state()
            return f"Quote analysis failed: {result.get('error', 'Unknown error')}"

        rec = result

        summary = ""
        for i, q in enumerate(rec['comparison_table'], start=1):
            summary += f"""
{i}. {q['supplier_name']}
   Unit: Rs.{q['unit_price']}
   Total: Rs.{q['total_cost']:,.0f}
   Delivery: {q['delivery_days']} days
   Terms: {q['payment_terms']}"""

        base_message = f"""Quote Comparison Complete

Item: {rec['po_data']['item_name']}
Quantity: {rec['po_data']['quantity']} units

Budget Check:
- Budget Limit: Rs.{50000:,.0f}
- Total Cost: Rs.{rec['po_data']['total_cost']:,.0f}
- Status: {rec['budget_status']}

Supplier Quotes:{summary}

RECOMMENDATION:
Supplier: {rec['selected_supplier']}
Total Cost: Rs.{rec['po_data']['total_cost']:,.0f}

Reasoning:
{rec['po_data']['justification']} """

        if rec.get('needs_user_approval'):
            self.pending_po_data = rec['po_data']
            self.state = "awaiting_po_approval"

            approval_question = self._generate_po_approval_question(
                rec['po_data']['item_name'],
                rec['selected_supplier'],
                rec['po_data']['total_cost'],
                rec['po_data']['delivery_days']
            )

            return f"{base_message}\n{approval_question}"
        else:
            self.decision_agent.approve_purchase_order(rec['po_data'], approved=True)

            self.communication_agent.send_notification('po_approved', {
                'po_number': rec['po_data']['po_number'],
                'item_name': rec['po_data']['item_name'],
                'supplier_name': rec['selected_supplier'],
                'quantity': rec['po_data']['quantity'],
                'total_cost': rec['po_data']['total_cost'],
                'expected_delivery_date': rec['po_data']['expected_delivery_date']
            })

            self._reset_state()
            return f"{base_message}\nPurchase order auto-approved and saved. Stakeholders have been notified."

    def _handle_notification_query(self, user_input: str) -> str:
        """Handle user queries about sent notifications"""
        log_info("Retrieving notification history", self.name)

        history = self.communication_agent.get_notification_history(limit=10)

        if not history:
            return "No notifications have been sent yet."

        output = "Recent Notifications:\n\n"
        for idx, notif in enumerate(history, 1):
            output += f"{idx}. Event: {notif['event_type']}\n"
            output += f"   Sent at: {notif['sent_at']}\n"
            output += f"   Status: {notif['status']}\n"
            output += f"   Recipients: {', '.join(notif['recipients'])}\n\n"

        return output

    def _handle_inbox_check(self, user_input: str) -> str:
        """Handle user requests to check inbox or get email summary"""
        log_info("Checking inbox for supplier emails", self.name)

        lower = user_input.lower()

        if any(keyword in lower for keyword in ["summarize", "summary"]):
            summary = self.communication_agent.summarize_supplier_emails(days=7)
            return summary
        else:
            quote_result = self.decision_agent.check_and_parse_quotes(
                self.last_item_code if self.last_item_code else None
            )

            update_result = self.communication_agent.check_inbox_for_updates(
                self.last_item_code if self.last_item_code else None
            )

            total_emails = quote_result['quotes_found'] + update_result['new_emails_count']

            if total_emails == 0:
                return "No new supplier emails found in inbox."

            parsed_count = len(quote_result['parsed_quotes'])

            output = f"Found {total_emails} new email(s) from suppliers.\n\n"
            output += f"- Quote emails: {quote_result['quotes_found']}\n"
            output += f"- Update emails: {update_result['new_emails_count']}\n"

            if quote_result['quotes_found'] > 0:
                output += f"\nSuccessfully parsed {parsed_count} quote(s).\n"

                for quote in quote_result['parsed_quotes']:
                    self.communication_agent.send_notification('quote_received', {
                        'item_name': quote.get('item_name', self.last_item_name),
                        'supplier_name': quote['supplier_name'],
                        'unit_price': quote['unit_price'],
                        'delivery_days': quote['delivery_days'],
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                output += "\nStakeholders have been notified about received quotes."
                output += "\nSay 'analyze quotes' when ready to compare all collected quotes."

            return output

    def _generate_po_approval_question(self, item_name, supplier_name, total_cost, delivery_days):
        """Generate varied PO approval question using LLM"""
        try:
            prompt = f"""Generate a natural, conversational question asking for purchase order approval.

Item: {item_name}
Supplier: {supplier_name}
Total Cost: Rs.{total_cost:,.2f}
Delivery: {delivery_days} days

Requirements:
- Keep it under 30 words
- Sound natural and varied
- Include key details (supplier, cost)
- Ask for yes/no approval
- No markdown, no quotes
- Direct question only

Generate ONLY the question text."""

            response = groq.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100
            )

            question = response.choices[0].message.content.strip()
            question = question.replace('*', '').replace('`', '').replace('"', '').replace("'", "")
            return question

        except Exception as e:
            log_error(f"Error generating approval question: {e}", self.name)
            return f"Approve purchase order for {item_name} from {supplier_name} at Rs.{total_cost:,.2f}? (yes/no)"

    def _handle_po_approval(self, intent: dict) -> str:
        """Handle PO approval/rejection"""
        if not self.pending_po_data:
            return "No pending purchase order to approve."

        if intent.get('response') == 'yes':
            self.decision_agent.approve_purchase_order(self.pending_po_data, approved=True)

            self.communication_agent.send_notification('po_approved', {
                'po_number': self.pending_po_data['po_number'],
                'item_name': self.pending_po_data['item_name'],
                'supplier_name': self.pending_po_data['supplier_name'],
                'quantity': self.pending_po_data['quantity'],
                'total_cost': self.pending_po_data['total_cost'],
                'expected_delivery_date': self.pending_po_data['expected_delivery_date']
            })

            po_number = self.pending_po_data['po_number']
            self.pending_po_data = None
            self._reset_state()
            return f"Purchase Order {po_number} approved and saved successfully! Stakeholders have been notified."
        else:
            self.decision_agent.approve_purchase_order(self.pending_po_data, approved=False)
            po_number = self.pending_po_data['po_number']
            self.pending_po_data = None
            self._reset_state()
            return f"Purchase Order {po_number} rejected and logged."

    def _handle_acknowledgment(self) -> str:
        """Handle casual acknowledgments naturally"""
        import random
        responses = [
            "Sure thing! Anything else I can help with?",
            "Got it. Let me know if you need anything.",
            "Alright! Just holler if you need me.",
            "No problem. I'm here when you need me.",
            "Sounds good. What else can I do for you?",
        ]

        return random.choice(responses)

    def _show_help(self) -> str:
        """Display help message"""
        return """I'm your Procurement Assistant! Here's what I can do:

Check Inventory & Order Status:
 Just ask about any item naturally - I'll analyze if we need to order

Find Suppliers:
 Ask me to find suppliers for any item and I'll search for the best options

Send RFQs:
 I can send professional RFQ emails to suppliers based on your preferences

Manage Pending Orders:
 Save RFQs for later and resume them whenever you're ready

Compare Quotes & Generate POs:
 Share supplier quotes with me and I'll analyze and recommend the best option

Check Inbox:
 I automatically monitor supplier emails and can check for new quotes anytime

View Notifications:
 Ask me what notifications I've sent to keep track of communications

Just talk naturally - I understand conversational language and will figure out what you need!"""

    def _handle_unclear_intent(self) -> str:
        """Handle unclear user input"""
        return "I didn't quite catch that. You can ask me to check an item's status, find suppliers, check inbox for quotes, or show pending orders. What would you like to do?"

    def _reset_state(self):
        """Reset conversation state for new flow"""
        self.state = "idle"
        self.last_item_code = None
        self.last_item_name = None
        self.last_quantity = None
        self.last_suppliers = None
        self.rfq_sent = False
        self.collected_quotes = []
        self.pending_po_data = None
        log_info("State reset - ready for new conversation", self.name)

    def _extract_item(self, text: str):
        """Extract item code from user input by matching with inventory"""
        try:
            inventory_df = self.load_csv('current_inventory.csv')
           
            text_lower = text.lower()
           
            for _, row in inventory_df.iterrows():
                item_name_lower = row['item_name'].lower()
                words = item_name_lower.split()
                if any(word in text_lower for word in words if len(word) > 3):
                    return row['item_code']
           
            return None
        except Exception as e:
            log_error(f"Failed to extract item: {e}", self.name)
            return None

    def _get_item_category(self, item_code: str) -> str:
        """Get item category from inventory CSV"""
        try:
            inventory_df = self.load_csv('current_inventory.csv')
           
            row = inventory_df[inventory_df['item_code'] == item_code]
            if not row.empty:
                item_name = row.iloc[0]['item_name'].lower()
               
                if any(word in item_name for word in ['screw', 'bolt', 'nut', 'fastener']):
                    return 'Fasteners & Hardware'
                elif any(word in item_name for word in ['plate', 'sheet', 'metal', 'steel', 'aluminum']):
                    return 'Raw Materials'
                elif any(word in item_name for word in ['oil', 'grease', 'lubricant', 'fluid']):
                    return 'Industrial Fluids'
                elif any(word in item_name for word in ['bearing', 'valve', 'motor']):
                    return 'Machinery Parts'
                else:
                    return 'General Supplies'
           
            return 'General Supplies'
        except Exception as e:
            log_error(f"Failed to get category: {e}", self.name)
            return 'General Supplies'


if __name__ == "__main__":
    print("Testing Agent 0 - Master Orchestrator")

    orchestrator = MasterOrchestrator()

    print("\n--- Conversation Simulation ---\n")

    print("User: check M8 screws")
    response1 = orchestrator.process_request("check M8 screws")
    print(f"\nAssistant: {response1}\n")

    print("User: i got quotes")
    response2 = orchestrator.process_request("i got quotes")
    print(f"\nAssistant: {response2}\n")

    print("User: analyze quotes")
    response3 = orchestrator.process_request("analyze quotes")
    print(f"\nAssistant: {response3}\n")

    print("\nAgent 0 test complete")
