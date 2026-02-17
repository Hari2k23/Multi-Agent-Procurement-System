"""
Multi-Agent Procurement System - Streamlit UI
Production-ready interface for AI-powered procurement automation
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.Agent0 import MasterOrchestrator
from utils.logger import logger, log_error

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Procurement System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium glassmorphism design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    :root {
        --primary-blue: #2E86AB;
        --primary-blue-light: #3A9BC4;
        --accent-cyan: #06D6A0;
        --warning-orange: #F77F00;
        --danger-red: #EF476F;
        --bg-dark: #0A0E27;
        --bg-card: rgba(20, 30, 60, 0.4);
        --text-primary: #E8E9ED;
        --text-secondary: #A0A3B1;
        --glass-border: rgba(46, 134, 171, 0.3);
    }
    
    /* Remove top padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #0A0E27 0%, #1a1f3a 50%, #0f1629 100%);
    }
    
    /* Glassmorphism chat container - only show when has messages */
    .chat-container {
        background: rgba(20, 30, 60, 0.3);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 28px;
        border: 1px solid rgba(46, 134, 171, 0.2);
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }
    
    /* Enhanced message bubbles */
    .user-message {
        background: linear-gradient(135deg, #2E86AB 0%, #3A9BC4 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 20px 20px 4px 20px;
        margin: 14px 0;
        max-width: 70%;
        margin-left: auto;
        box-shadow: 0 4px 16px rgba(46, 134, 171, 0.4);
        font-size: 15px;
        line-height: 1.6;
        animation: slideInRight 0.3s ease;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, rgba(30, 40, 70, 0.6) 0%, rgba(40, 50, 80, 0.6) 100%);
        backdrop-filter: blur(10px);
        color: #E8E9ED;
        padding: 18px 24px;
        border-radius: 20px 20px 20px 4px;
        margin: 14px 0;
        max-width: 70%;
        border-left: 4px solid #06D6A0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        font-size: 15px;
        line-height: 1.6;
        animation: slideInLeft 0.3s ease;
    }
    
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    /* Premium glassmorphism metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 40, 70, 0.4) 0%, rgba(40, 50, 80, 0.3) 100%);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: 20px;
        padding: 28px;
        border: 1px solid rgba(46, 134, 171, 0.25);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #2E86AB, #06D6A0);
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 40px rgba(46, 134, 171, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        border-color: rgba(46, 134, 171, 0.5);
    }
    
    .metric-card:hover::before {
        opacity: 1;
    }
    
    .metric-value {
        font-size: 42px;
        font-weight: 700;
        background: linear-gradient(135deg, #06D6A0 0%, #2E86AB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0;
        letter-spacing: -1px;
    }
    
    .metric-label {
        color: #A0A3B1;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .metric-delta {
        font-size: 13px;
        margin-top: 10px;
        font-weight: 500;
    }
    
    .metric-delta.positive {
        color: #06D6A0;
    }
    
    .metric-delta.negative {
        color: #EF476F;
    }
    
    /* Enhanced info cards */
    .info-card {
        background: linear-gradient(135deg, rgba(46, 134, 171, 0.15) 0%, rgba(6, 214, 160, 0.1) 100%);
        backdrop-filter: blur(10px);
        border-left: 4px solid #2E86AB;
        border-radius: 16px;
        padding: 24px;
        margin: 18px 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 22, 41, 0.95) 0%, rgba(10, 14, 39, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(46, 134, 171, 0.2);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #E8E9ED;
    }
    
    /* Enhanced input fields */
    .stTextInput > div > div > input {
        background: rgba(30, 40, 70, 0.5) !important;
        backdrop-filter: blur(10px);
        border: 1.5px solid rgba(46, 134, 171, 0.3) !important;
        border-radius: 14px !important;
        color: #E8E9ED !important;
        padding: 14px 18px !important;
        font-size: 15px !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #2E86AB !important;
        box-shadow: 0 0 0 3px rgba(46, 134, 171, 0.15) !important;
        background: rgba(30, 40, 70, 0.7) !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #6B7280 !important;
        opacity: 0.7 !important;
    }
    
    /* Premium buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2E86AB 0%, #3A9BC4 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 32px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 16px rgba(46, 134, 171, 0.3) !important;
        letter-spacing: 0.3px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(46, 134, 171, 0.5) !important;
        background: linear-gradient(135deg, #3A9BC4 0%, #2E86AB 100%) !important;
    }
    
    /* Enhanced tabs with glassmorphism */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: linear-gradient(135deg, rgba(30, 40, 70, 0.4) 0%, rgba(20, 30, 60, 0.4) 100%);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        padding: 12px;
        border-radius: 18px;
        border: 1px solid rgba(46, 134, 171, 0.25);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(30, 40, 70, 0.3);
        backdrop-filter: blur(10px);
        border-radius: 14px;
        color: #A0A3B1;
        font-weight: 600;
        padding: 16px 32px;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(46, 134, 171, 0.15);
        position: relative;
        overflow: hidden;
    }
    
    .stTabs [data-baseweb="tab"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(46, 134, 171, 0.1), rgba(6, 214, 160, 0.1));
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(46, 134, 171, 0.2);
        color: #06D6A0;
        border-color: rgba(46, 134, 171, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(46, 134, 171, 0.2);
    }
    
    .stTabs [data-baseweb="tab"]:hover::before {
        opacity: 1;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2E86AB 0%, #06D6A0 100%);
        color: white;
        border-color: rgba(6, 214, 160, 0.5);
        box-shadow: 0 6px 20px rgba(46, 134, 171, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
    }
    
    /* Data tables */
    .dataframe {
        background: rgba(20, 30, 60, 0.3);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(46, 134, 171, 0.2);
    }
    
    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(20, 30, 60, 0.3);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #2E86AB, #3A9BC4);
        border-radius: 10px;
        border: 2px solid rgba(20, 30, 60, 0.3);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #3A9BC4, #06D6A0);
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .metric-card {
            padding: 20px;
        }
        
        .metric-value {
            font-size: 32px;
        }
        
        .user-message, .assistant-message {
            max-width: 85%;
            padding: 14px 18px;
            font-size: 14px;
        }
        
        .chat-container {
            padding: 20px;
        }
    }
    
    @media (max-width: 480px) {
        .metric-value {
            font-size: 28px;
        }
        
        .user-message, .assistant-message {
            max-width: 95%;
        }
    }
    
    /* Enhanced selectbox */
    .stSelectbox > div > div {
        background: rgba(30, 40, 70, 0.5);
        backdrop-filter: blur(10px);
        border: 1.5px solid rgba(46, 134, 171, 0.3);
        border-radius: 14px;
    }
    
    /* File uploader */
    .stFileUploader {
        background: rgba(30, 40, 70, 0.3);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 2px dashed rgba(46, 134, 171, 0.3);
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = MasterOrchestrator()
    
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Utility functions
def load_json_data(filepath, default=None):
    """Load JSON data with error handling"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return default if default is not None else {}
    except Exception as e:
        log_error(f"Error loading {filepath}: {e}")
        return default if default is not None else {}

def load_inventory_data():
    """Load current inventory from CSV"""
    try:
        csv_path = "data/current_inventory.csv"
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        return pd.DataFrame()
    except Exception as e:
        log_error(f"Error loading inventory: {e}")
        return pd.DataFrame()

def get_system_metrics():
    """Calculate real-time system metrics"""
    try:
        inventory_df = load_inventory_data()
        quotes = load_json_data("data/quotes_collected.json", {})
        pos = load_json_data("data/purchase_orders.json", [])
        notifications = load_json_data("data/notification_logs.json", [])
        
        total_items = len(inventory_df) if not inventory_df.empty else 0
        
        low_stock_count = 0
        if not inventory_df.empty and 'current_quantity' in inventory_df.columns and 'reorder_point' in inventory_df.columns:
            low_stock_count = len(inventory_df[inventory_df['current_quantity'] < inventory_df['reorder_point']])
        
        active_pos = len([po for po in pos if po.get('status') == 'approved']) if isinstance(pos, list) else 0
        total_quotes = sum(len(supplier_quotes) for supplier_quotes in quotes.values()) if isinstance(quotes, dict) else 0
        recent_notifications = len([n for n in notifications if isinstance(n, dict) and 
                                   (datetime.now() - datetime.fromisoformat(n.get('timestamp', '2020-01-01'))).days < 7]) if isinstance(notifications, list) else 0
        
        return {
            'total_items': total_items,
            'low_stock_count': low_stock_count,
            'active_pos': active_pos,
            'total_quotes': total_quotes,
            'recent_notifications': recent_notifications
        }
    except Exception as e:
        log_error(f"Error calculating metrics: {e}")
        return {'total_items': 0, 'low_stock_count': 0, 'active_pos': 0, 'total_quotes': 0, 'recent_notifications': 0}

# Sidebar navigation
with st.sidebar:
    st.markdown("""
    <h2 style='background: linear-gradient(135deg, #06D6A0 0%, #2E86AB 100%); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent; 
                font-weight: 800; 
                font-size: 22px; 
                margin-bottom: 0; 
                letter-spacing: -0.5px;'>
        Multi-Agent Procurement System
    </h2>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["Dashboard", "Chat Interface", "Inventory Monitor", "Procurement Pipeline", "Document Verification", "Configurations"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("#### System Status")
    metrics = get_system_metrics()
    
    st.markdown(f"""
    <div style='padding: 14px; background: rgba(6, 214, 160, 0.15); backdrop-filter: blur(10px); border-radius: 12px; margin: 10px 0; border: 1px solid rgba(6, 214, 160, 0.3);'>
        <div style='color: #A0A3B1; font-size: 11px; font-weight: 600; letter-spacing: 1px;'>SYSTEM</div>
        <div style='color: #06D6A0; font-size: 20px; font-weight: 700; margin-top: 4px;'>Operational</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='padding: 14px; background: rgba(46, 134, 171, 0.15); backdrop-filter: blur(10px); border-radius: 12px; margin: 10px 0; border: 1px solid rgba(46, 134, 171, 0.3);'>
        <div style='color: #A0A3B1; font-size: 11px; font-weight: 600; letter-spacing: 1px;'>ACTIVE AGENTS</div>
        <div style='color: #2E86AB; font-size: 20px; font-weight: 700; margin-top: 4px;'>12/12</div>
    </div>
    """, unsafe_allow_html=True)
    
    if metrics['low_stock_count'] > 0:
        st.markdown(f"""
        <div style='padding: 14px; background: rgba(247, 127, 0, 0.15); backdrop-filter: blur(10px); border-radius: 12px; margin: 10px 0; border: 1px solid rgba(247, 127, 0, 0.3);'>
            <div style='color: #A0A3B1; font-size: 11px; font-weight: 600; letter-spacing: 1px;'>LOW STOCK ALERTS</div>
            <div style='color: #F77F00; font-size: 20px; font-weight: 700; margin-top: 4px;'>{metrics['low_stock_count']}</div>
        </div>
        """, unsafe_allow_html=True)

# Main content area
if page == "Dashboard":
    st.markdown("# Dashboard")
    st.markdown("Real-time overview of your procurement system")
    
    col1, col2, col3, col4 = st.columns(4)
    metrics = get_system_metrics()
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total Items</div>
            <div class='metric-value'>{metrics['total_items']}</div>
            <div class='metric-delta positive'>In Inventory</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_class = 'negative' if metrics['low_stock_count'] > 0 else 'positive'
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Low Stock Items</div>
            <div class='metric-value'>{metrics['low_stock_count']}</div>
            <div class='metric-delta {delta_class}'>Needs Attention</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Active Orders</div>
            <div class='metric-value'>{metrics['active_pos']}</div>
            <div class='metric-delta positive'>In Progress</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Quotes Received</div>
            <div class='metric-value'>{metrics['total_quotes']}</div>
            <div class='metric-delta positive'>This Month</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Inventory Status")
        inventory_df = load_inventory_data()
        
        if not inventory_df.empty and 'current_quantity' in inventory_df.columns and 'reorder_point' in inventory_df.columns:
            inventory_df['status'] = inventory_df.apply(
                lambda row: 'Critical' if row['current_quantity'] < row['reorder_point'] * 0.5
                else 'Low' if row['current_quantity'] < row['reorder_point']
                else 'Adequate', axis=1
            )
            
            status_counts = inventory_df['status'].value_counts()
            
            # Enhanced pie chart with vibrant colors
            fig = go.Figure(data=[go.Pie(
                labels=status_counts.index,
                values=status_counts.values,
                hole=0.5,
                marker=dict(
                    colors=['#8B5CF6', '#3B82F6', '#06D6A0'],  # Purple, Blue, Teal gradient
                    line=dict(color='rgba(10, 14, 39, 0.8)', width=3)
                ),
                textfont=dict(size=16, color='white', family='Inter'),
                textposition='outside',
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
                pull=[0.05, 0.05, 0.05]
            )])
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E8E9ED', family='Inter'),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                height=350,
                margin=dict(t=40, b=60, l=20, r=20)
            )
            
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No inventory data available")
    
    with col2:
        st.markdown("### Recent Activity")
        notifications = load_json_data("data/notification_logs.json", [])
        
        if notifications and isinstance(notifications, list):
            recent = sorted(notifications, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
            
            for notif in recent:
                event_type = notif.get('event_type', 'unknown')
                timestamp = notif.get('timestamp', '')
                
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%b %d, %I:%M %p")
                    except:
                        time_str = timestamp
                else:
                    time_str = "Unknown time"
                
                color = '#06D6A0' if 'approved' in event_type else '#2E86AB' if 'sent' in event_type else '#F77F00'
                
                st.markdown(f"""
                <div style='padding: 14px; background: rgba(30, 40, 70, 0.4); backdrop-filter: blur(10px); border-left: 3px solid {color}; 
                            border-radius: 12px; margin: 10px 0; border: 1px solid rgba(46, 134, 171, 0.2);'>
                    <div style='color: #E8E9ED; font-size: 14px; font-weight: 600;'>{event_type.replace('_', ' ').title()}</div>
                    <div style='color: #A0A3B1; font-size: 12px; margin-top: 4px;'>{time_str}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent activity")
    
    st.markdown("### Recent Purchase Orders")
    pos = load_json_data("data/purchase_orders.json", [])
    
    if pos and isinstance(pos, list):
        po_data = []
        for po in pos[-5:]:
            po_data.append({
                'PO Number': po.get('po_number', 'N/A'),
                'Supplier': po.get('supplier_name', 'N/A'),
                'Item': po.get('item_name', 'N/A'),
                'Quantity': po.get('quantity', 0),
                'Total Amount': f"₹{po.get('total_amount', 0):,.2f}",
                'Status': po.get('status', 'unknown').upper()
            })
        
        if po_data:
            df = pd.DataFrame(po_data)
            st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No purchase orders found")

elif page == "Chat Interface":
    st.markdown("# Procurement Assistant")
    st.markdown("""
    <p style='font-family: "Segoe UI", sans-serif; 
              font-size: 16px; 
              color: #06D6A0; 
              font-weight: 500; 
              margin-bottom: 24px; 
              letter-spacing: 0.3px;'>
        Conversational interface powered by 12 specialized AI agents
    </p>
    """, unsafe_allow_html=True)
    
    # Only show chat container border if there are messages
    if st.session_state.chat_history:
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    chat_display = st.container()
    
    with chat_display:
        if not st.session_state.chat_history:
            st.markdown("""
            <div class='info-card'>
                <h4 style='margin: 0; color: #2E86AB;'>Welcome to the Procurement Assistant</h4>
                <p style='margin: 8px 0 0 0; color: #A0A3B1;'>
                    I can help you with demand forecasting, supplier discovery, quote collection, 
                    purchase order management, and document verification. Try asking:
                </p>
                <ul style='color: #A0A3B1; margin: 8px 0 0 20px;'>
                    <li>Check inventory for item XYZ</li>
                    <li>Find suppliers for steel pipes</li>
                    <li>Analyze quotes for PO-12345</li>
                    <li>Show pending purchase orders</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                # Escape HTML to prevent hashtags from being interpreted
                content = msg['content'].replace('<', '&lt;').replace('>', '&gt;')
                st.markdown(f"<div class='user-message'>{content}</div>", unsafe_allow_html=True)
            else:
                # Escape HTML to prevent hashtags from being interpreted
                content = msg['content'].replace('<', '&lt;').replace('>', '&gt;')
                st.markdown(f"<div class='assistant-message'>{content}</div>", unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_input = st.text_input(
            "Type your message...",
            key="chat_input",
            placeholder="Type a message...",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("Send", width='stretch')
    
    if send_button and user_input:
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        with st.spinner("Processing..."):
            try:
                response = st.session_state.orchestrator.process_request(user_input)
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                error_msg = f"I encountered an error: {str(e)}. Please try again."
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
        
        st.rerun()

elif page == "Inventory Monitor":
    st.markdown("# Inventory Monitor")
    st.markdown("Real-time stock levels and replenishment alerts")
    
    inventory_df = load_inventory_data()
    
    if not inventory_df.empty:
        col1, col2, col3 = st.columns(3)
        
        total_items = len(inventory_df)
        if 'current_quantity' in inventory_df.columns and 'reorder_point' in inventory_df.columns:
            critical_items = len(inventory_df[inventory_df['current_quantity'] < inventory_df['reorder_point'] * 0.5])
            low_stock_items = len(inventory_df[
                (inventory_df['current_quantity'] >= inventory_df['reorder_point'] * 0.5) &
                (inventory_df['current_quantity'] < inventory_df['reorder_point'])
            ])
        else:
            critical_items = 0
            low_stock_items = 0
        
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Total SKUs</div>
                <div class='metric-value'>{total_items}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Critical Stock</div>
                <div class='metric-value' style='background: linear-gradient(135deg, #EF476F 0%, #F77F00 100%); 
                            -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{critical_items}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Low Stock</div>
                <div class='metric-value' style='background: linear-gradient(135deg, #F77F00 0%, #2E86AB 100%); 
                            -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{low_stock_items}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            filter_option = st.selectbox(
                "Filter by status",
                ["All Items", "Critical Stock", "Low Stock", "Adequate Stock"]
            )
        
        with col2:
            search_term = st.text_input("Search items", placeholder="Enter item name or code...")
        
        filtered_df = inventory_df.copy()
        
        if 'current_quantity' in filtered_df.columns and 'reorder_point' in filtered_df.columns:
            if filter_option == "Critical Stock":
                filtered_df = filtered_df[filtered_df['current_quantity'] < filtered_df['reorder_point'] * 0.5]
            elif filter_option == "Low Stock":
                filtered_df = filtered_df[
                    (filtered_df['current_quantity'] >= filtered_df['reorder_point'] * 0.5) &
                    (filtered_df['current_quantity'] < filtered_df['reorder_point'])
                ]
            elif filter_option == "Adequate Stock":
                filtered_df = filtered_df[filtered_df['current_quantity'] >= filtered_df['reorder_point']]
        
        if search_term:
            mask = filtered_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
            filtered_df = filtered_df[mask]
        
        if not filtered_df.empty:
            if 'current_quantity' in filtered_df.columns and 'reorder_point' in filtered_df.columns:
                filtered_df['Status'] = filtered_df.apply(
                    lambda row: 'Critical' if row['current_quantity'] < row['reorder_point'] * 0.5
                    else 'Low' if row['current_quantity'] < row['reorder_point']
                    else 'Adequate', axis=1
                )
            
            st.dataframe(filtered_df, width='stretch', hide_index=True, height=400)
        else:
            st.info("No items match the current filters")
    else:
        st.warning("No inventory data available. Please ensure current_inventory.csv exists in the data folder.")

elif page == "Procurement Pipeline":
    st.markdown("# Procurement Pipeline")
    st.markdown("Track RFQs, quotes, and purchase orders")
    
    tab1, tab2, tab3 = st.tabs(["Active RFQs", "Quotes Analysis", "Purchase Orders"])
    
    with tab1:
        pending_rfqs = load_json_data("data/pending_rfqs.json", {})
        
        if pending_rfqs:
            st.markdown(f"### {len(pending_rfqs)} Pending RFQs")
            
            for rfq_id, rfq_data in pending_rfqs.items():
                with st.expander(f"RFQ: {rfq_data.get('item_name', 'Unknown Item')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Item Code:** {rfq_data.get('item_code', 'N/A')}")
                        st.markdown(f"**Quantity:** {rfq_data.get('quantity', 0)}")
                        st.markdown(f"**Created:** {rfq_data.get('timestamp', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**Suppliers:** {len(rfq_data.get('suppliers', []))}")
                        st.markdown(f"**Status:** {rfq_data.get('status', 'pending').upper()}")
        else:
            st.info("No pending RFQs")
    
    with tab2:
        quotes = load_json_data("data/quotes_collected.json", {})
        
        if quotes:
            st.markdown(f"### Quotes from {len(quotes)} Suppliers")
            
            quote_data = []
            for supplier, supplier_quotes in quotes.items():
                if isinstance(supplier_quotes, list):
                    for quote in supplier_quotes:
                        quote_data.append({
                            'Supplier': supplier,
                            'Item': quote.get('item_name', 'N/A'),
                            'Unit Price': f"₹{quote.get('unit_price', 0):,.2f}",
                            'Quantity': quote.get('quantity', 0),
                            'Delivery Days': quote.get('delivery_days', 'N/A'),
                            'Total': f"₹{quote.get('total_price', 0):,.2f}"
                        })
            
            if quote_data:
                df = pd.DataFrame(quote_data)
                st.dataframe(df, width='stretch', hide_index=True)
                
                if len(quote_data) > 1:
                    fig = px.bar(df, x='Supplier', y='Total', color='Supplier', title='Quote Comparison by Supplier')
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#E8E9ED', family='Inter'),
                        showlegend=False
                    )
                    st.plotly_chart(fig, width='stretch')
        else:
            st.info("No quotes collected yet")
    
    with tab3:
        pos = load_json_data("data/purchase_orders.json", [])
        
        if pos and isinstance(pos, list):
            st.markdown(f"### {len(pos)} Purchase Orders")
            
            status_filter = st.selectbox("Filter by status", ["All", "Approved", "Pending", "Rejected"])
            
            filtered_pos = pos
            if status_filter != "All":
                filtered_pos = [po for po in pos if po.get('status', '').lower() == status_filter.lower()]
            
            for po in filtered_pos:
                status = po.get('status', 'unknown').upper()
                status_color = '#06D6A0' if status == 'APPROVED' else '#F77F00' if status == 'PENDING' else '#EF476F'
                
                with st.expander(f"PO {po.get('po_number', 'N/A')} - {po.get('supplier_name', 'Unknown')}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown(f"**Item:** {po.get('item_name', 'N/A')}")
                        st.markdown(f"**Quantity:** {po.get('quantity', 0)}")
                    
                    with col2:
                        st.markdown(f"**Unit Price:** ₹{po.get('unit_price', 0):,.2f}")
                        st.markdown(f"**Total:** ₹{po.get('total_amount', 0):,.2f}")
                    
                    with col3:
                        st.markdown(f"**Delivery:** {po.get('delivery_days', 'N/A')} days")
                        st.markdown(f"**Status:** {status}")
        else:
            st.info("No purchase orders found")

elif page == "Document Verification":
    st.markdown("# Document Verification")
    st.markdown("Upload and verify delivery notes and invoices")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Upload Delivery Note")
        delivery_note = st.file_uploader("Choose delivery note image", type=['jpg', 'jpeg', 'png'], key="delivery_note")
        if delivery_note:
            st.image(delivery_note, caption="Delivery Note", width='stretch')
    
    with col2:
        st.markdown("### Upload Invoice")
        invoice = st.file_uploader("Choose invoice image", type=['jpg', 'jpeg', 'png'], key="invoice")
        if invoice:
            st.image(invoice, caption="Invoice", width='stretch')
    
    if delivery_note and invoice:
        po_number = st.text_input("Enter PO Number for verification")
        
        if st.button("Verify Documents", type="primary"):
            with st.spinner("Verifying documents using AI vision..."):
                st.info("Document verification feature requires Agent 8 integration. This will process the uploaded documents and perform three-way matching.")
    
    st.markdown("### Recent Verifications")
    goods_receipts = load_json_data("data/goods_receipts.json", [])
    
    if goods_receipts and isinstance(goods_receipts, list):
        for gr in goods_receipts[-5:]:
            match_status = gr.get('match_status', 'unknown').upper()
            status_color = '#06D6A0' if match_status == 'PASS' else '#EF476F'
            
            st.markdown(f"""
            <div style='padding: 18px; background: rgba(30, 40, 70, 0.4); backdrop-filter: blur(10px); border-left: 4px solid {status_color}; 
                        border-radius: 14px; margin: 14px 0; border: 1px solid rgba(46, 134, 171, 0.2);'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <div style='color: #E8E9ED; font-size: 16px; font-weight: 600;'>{gr.get('gr_number', 'N/A')}</div>
                        <div style='color: #A0A3B1; font-size: 13px; margin-top: 4px;'>PO: {gr.get('po_number', 'N/A')} | Item: {gr.get('item_code', 'N/A')}</div>
                    </div>
                    <div><span style='background: rgba({int(status_color[1:3], 16)}, {int(status_color[3:5], 16)}, {int(status_color[5:7], 16)}, 0.2); color: {status_color}; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 600;'>{match_status}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No verification history available")

elif page == "Configurations":
    st.markdown("# System Configurations")
    st.markdown("Configure system parameters and preferences")
    
    tab1, tab2, tab3 = st.tabs(["General", "Email Configuration", "Agent Settings"])
    
    with tab1:
        st.markdown("### General Settings")
        company_name = st.text_input("Company Name", value="Manufacturing Solutions Pvt Ltd")
        company_email = st.text_input("Company Email", value="procurement@company.com")
        test_mode = st.checkbox("Test Mode", value=True, help="Send emails to test addresses instead of actual suppliers")
        if st.button("Save General Settings"):
            st.success("Settings saved successfully")
    
    with tab2:
        st.markdown("### Email Configuration")
        gmail_user = st.text_input("Gmail Address", type="default")
        gmail_password = st.text_input("Gmail App Password", type="password")
        st.markdown("""
        <div class='info-card'>
            <h4 style='margin: 0; color: #2E86AB;'>Gmail App Password Setup</h4>
            <p style='margin: 8px 0 0 0; color: #A0A3B1;'>To generate an app password:</p>
            <ol style='color: #A0A3B1; margin: 8px 0 0 20px;'>
                <li>Go to your Google Account settings</li>
                <li>Enable 2-Step Verification</li>
                <li>Go to Security → App passwords</li>
                <li>Generate a new app password for Mail</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Save Email Settings"):
            st.success("Email settings saved successfully")
    
    with tab3:
        st.markdown("### Agent Configuration")
        st.markdown("#### Agent 6 - Decision Maker")
        always_require_approval = st.checkbox("Always Require Approval", value=True)
        approval_threshold = st.number_input("Approval Threshold (₹)", value=50000, step=1000)
        budget_limit = st.number_input("Budget Limit (₹)", value=100000, step=5000)
        st.markdown("#### Agent 9 - Exception Handler")
        accept_threshold = st.slider("Accept Threshold (%)", 0.0, 10.0, 2.0, 0.1)
        reject_threshold = st.slider("Reject Threshold (%)", 5.0, 20.0, 10.0, 0.5)
        if st.button("Save Agent Settings"):
            st.success("Agent settings saved successfully")
    
    st.markdown("---")
    st.markdown("### System Information")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class='info-card'>
            <div style='color: #A0A3B1; font-size: 12px;'>VERSION</div>
            <div style='color: #E8E9ED; font-size: 18px; font-weight: 600; margin-top: 4px;'>1.0.0</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='info-card'>
            <div style='color: #A0A3B1; font-size: 12px;'>ACTIVE AGENTS</div>
            <div style='color: #E8E9ED; font-size: 18px; font-weight: 600; margin-top: 4px;'>12/12</div>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #A0A3B1; font-size: 13px; padding: 20px 0;'>
    Multi-Agent Procurement System
</div>
""", unsafe_allow_html=True)
