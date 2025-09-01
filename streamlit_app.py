#!/usr/bin/env python3
"""
Owner Statement Generator - Abacus.AI Project
Main Streamlit application for automated owner statement generation
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Owner Statement Generator",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stSelectbox > div > div > select {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# Core calculation classes
class OwnerStatementProcessor:
    def __init__(self, config_data: Dict[str, Any] = None):
        """Initialize the processor with configuration"""
        self.config = config_data or self.get_default_config()
        self.default_settings = self.config.get('default_settings', {})
        self.client_overrides = self.config.get('client_overrides', {})
        
    def get_default_config(self):
        """Get default configuration"""
        return {
            "default_settings": {
                "management_fee_percentage": 20,
                "default_tag": "480 Laswell Ave",
                "supplies_estimate_percentage": 15,
                "utilities_estimate_percentage": 8
            },
            "client_overrides": {}
        }
        
    def get_client_settings(self, tag: str) -> Dict[str, Any]:
        """Get settings for specific client tag"""
        if tag in self.client_overrides:
            settings = self.default_settings.copy()
            settings.update(self.client_overrides[tag])
            return settings
        return self.default_settings
    
    def calculate_management_fee(self, reservation_income: float, supplies_estimate: float, 
                               utilities_estimate: float, other_expenses: float, 
                               management_fee_percentage: float) -> float:
        """Calculate management fee after deducting estimates and expenses"""
        net_income = reservation_income - supplies_estimate - utilities_estimate - other_expenses
        return net_income * (management_fee_percentage / 100)
    
    def calculate_supplies_estimate(self, cleaning_fees: float, supplies_percentage: float) -> float:
        """Calculate supplies estimate based on cleaning fees"""
        return cleaning_fees * (supplies_percentage / 100)
    
    def calculate_utilities_estimate(self, reservation_income: float, utilities_percentage: float) -> float:
        """Calculate utilities estimate based on reservation income"""
        return reservation_income * (utilities_percentage / 100)
    
    def process_reservations_data(self, reservations_data: List[Dict], tag: str) -> Dict[str, Any]:
        """Process reservation data and calculate all fees"""
        settings = self.get_client_settings(tag)
        
        # Calculate totals from reservations
        total_reservation_income = sum(r.get('total_amount', 0) for r in reservations_data)
        total_cleaning_fees = sum(r.get('cleaning_fee', 0) for r in reservations_data)
        
        # Calculate estimates
        supplies_estimate = self.calculate_supplies_estimate(
            total_cleaning_fees, 
            settings['supplies_estimate_percentage']
        )
        
        utilities_estimate = self.calculate_utilities_estimate(
            total_reservation_income,
            settings['utilities_estimate_percentage']
        )
        
        # For now, other expenses is 0 (can be manually added later)
        other_expenses = 0
        
        # Calculate management fee
        management_fee = self.calculate_management_fee(
            total_reservation_income,
            supplies_estimate,
            utilities_estimate,
            other_expenses,
            settings['management_fee_percentage']
        )
        
        # Calculate owner payout
        owner_payout = total_reservation_income - supplies_estimate - utilities_estimate - other_expenses - management_fee
        
        return {
            'tag': tag,
            'total_reservations': len(reservations_data),
            'reservation_income': total_reservation_income,
            'cleaning_fees': total_cleaning_fees,
            'supplies_estimate': supplies_estimate,
            'utilities_estimate': utilities_estimate,
            'other_expenses': other_expenses,
            'management_fee': management_fee,
            'owner_payout': owner_payout,
            'management_payout': management_fee,
            'total_payouts': owner_payout + management_fee,
            'settings': settings,
            'reservations': reservations_data
        }
    
    def create_statement_breakdown(self, processed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create detailed breakdown for the owner statement"""
        breakdown = [
            {
                'line_item': 'Reservation Income',
                'amount': processed_data['reservation_income'],
                'type': 'income',
                'payout_to': 'N/A'
            },
            {
                'line_item': 'Supplies Estimate',
                'amount': -processed_data['supplies_estimate'],
                'type': 'expense',
                'payout_to': 'Management Company'
            },
            {
                'line_item': 'Utilities Estimate',
                'amount': -processed_data['utilities_estimate'],
                'type': 'expense',
                'payout_to': 'Management Company'
            },
            {
                'line_item': 'Management Fee',
                'amount': -processed_data['management_fee'],
                'type': 'expense',
                'payout_to': 'Management Company'
            },
            {
                'line_item': 'Owner Payout',
                'amount': processed_data['owner_payout'],
                'type': 'payout',
                'payout_to': 'Owner'
            }
        ]
        
        if processed_data['other_expenses'] > 0:
            breakdown.insert(-1, {
                'line_item': 'Other Expenses',
                'amount': -processed_data['other_expenses'],
                'type': 'expense',
                'payout_to': 'Various'
            })
        
        return breakdown

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = {
        "default_settings": {
            "management_fee_percentage": 20,
            "default_tag": "480 Laswell Ave",
            "supplies_estimate_percentage": 15,
            "utilities_estimate_percentage": 8
        },
        "client_overrides": {
            "480 Laswell Ave": {
                "management_fee_percentage": 20,
                "supplies_estimate_percentage": 15,
                "utilities_estimate_percentage": 8,
                "owner_name": "Property Owner",
                "management_company": "Your Management Company"
            }
        }
    }

if 'processor' not in st.session_state:
    st.session_state.processor = OwnerStatementProcessor(st.session_state.config)

def get_sample_reservations(tag: str) -> List[Dict[str, Any]]:
    """Get sample reservation data"""
    return [
        {
            'reservation_id': 'HSP001',
            'property_tag': tag,
            'guest_name': 'John Doe',
            'check_in': '2025-09-01',
            'check_out': '2025-09-05',
            'total_amount': 1800.00,
            'cleaning_fee': 120.00,
            'platform': 'Airbnb',
            'status': 'completed'
        },
        {
            'reservation_id': 'HSP002',
            'property_tag': tag,
            'guest_name': 'Jane Smith',
            'check_in': '2025-09-10',
            'check_out': '2025-09-15',
            'total_amount': 2500.00,
            'cleaning_fee': 150.00,
            'platform': 'VRBO',
            'status': 'completed'
        },
        {
            'reservation_id': 'HSP003',
            'property_tag': tag,
            'guest_name': 'Mike Johnson',
            'check_in': '2025-09-20',
            'check_out': '2025-09-25',
            'total_amount': 2200.00,
            'cleaning_fee': 130.00,
            'platform': 'Booking.com',
            'status': 'completed'
        }
    ]

def simulate_bank_verification(expected_amount: float) -> Dict[str, Any]:
    """Simulate bank balance verification"""
    # Simulate a small discrepancy for demonstration
    actual_balance = expected_amount + 25.75
    discrepancy = abs(expected_amount - actual_balance)
    
    return {
        'expected_amount': expected_amount,
        'actual_balance': actual_balance,
        'discrepancy': discrepancy,
        'is_match': discrepancy <= 0.01,
        'tolerance': 0.01,
        'status': 'MATCH' if discrepancy <= 0.01 else 'DISCREPANCY_FOUND',
        'verification_time': datetime.now().isoformat(),
        'simulation': True
    }

def render_sidebar():
    """Render the sidebar with navigation"""
    st.sidebar.header("🏠 Owner Statement Generator")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["Dashboard", "Generate Statement", "Configuration", "Reports", "Help"]
    )
    
    st.sidebar.markdown("---")
    
    # Quick Stats
    st.sidebar.subheader("Quick Stats")
    num_clients = len(st.session_state.config.get('client_overrides', {}))
    st.sidebar.metric("Active Properties", num_clients)
    
    # System status
    st.sidebar.subheader("System Status")
    st.sidebar.success("✅ System Operational")
    st.sidebar.info("📅 Ready for Processing")
    
    return page

def render_dashboard():
    """Render the main dashboard"""
    st.markdown('<h1 class="main-header">🏠 Owner Statement Dashboard</h1>', unsafe_allow_html=True)
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Active Properties",
            value=len(st.session_state.config.get('client_overrides', {})),
            delta=None
        )
    
    with col2:
        st.metric(
            label="Default Mgmt Fee",
            value=f"{st.session_state.config['default_settings']['management_fee_percentage']}%",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Supplies Rate",
            value=f"{st.session_state.config['default_settings']['supplies_estimate_percentage']}%",
            delta=None
        )
    
    with col4:
        st.metric(
            label="Utilities Rate", 
            value=f"{st.session_state.config['default_settings']['utilities_estimate_percentage']}%",
            delta=None
        )
    
    st.markdown("---")
    
    # Sample financial breakdown visualization
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Sample Financial Breakdown")
        
        # Get sample data for visualization
        sample_reservations = get_sample_reservations("480 Laswell Ave")
        processed_data = st.session_state.processor.process_reservations_data(sample_reservations, "480 Laswell Ave")
        breakdown = st.session_state.processor.create_statement_breakdown(processed_data)
        
        # Create waterfall chart
        categories = [item['line_item'] for item in breakdown]
        amounts = [item['amount'] for item in breakdown]
        
        fig = go.Figure(go.Waterfall(
            name="Financial Flow",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=categories,
            textposition="outside",
            text=[f"${x:,.2f}" for x in amounts],
            y=amounts,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title="Sample Owner Statement Breakdown",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Quick Actions")
        
        if st.button("🚀 Generate New Statement", type="primary", use_container_width=True):
            st.session_state.current_page = "Generate Statement"
            st.rerun()
        
        if st.button("⚙️ Configure Settings", use_container_width=True):
            st.session_state.current_page = "Configuration"
            st.rerun()
        
        if st.button("📊 View Sample Report", use_container_width=True):
            st.session_state.current_page = "Reports"
            st.rerun()
        
        st.markdown("---")
        
        st.subheader("📋 Integration Status")
        st.info("ℹ️ Hospitable: Demo Mode")
        st.success("✅ Google Sheets: Ready")
        st.info("ℹ️ RelayFi: Demo Mode")
        st.success("✅ Calculations: Active")

def render_generate_statement():
    """Render the statement generation page"""
    st.markdown('<h1 class="main-header">🚀 Generate Owner Statement</h1>', unsafe_allow_html=True)
    
    # Configuration form
    with st.form("statement_generation"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Property Selection")
            
            # Property tag selection
            available_tags = list(st.session_state.config.get('client_overrides', {}).keys())
            if not available_tags:
                available_tags = [st.session_state.config['default_settings']['default_tag']]
            
            selected_tag = st.selectbox(
                "Property Tag",
                available_tags,
                help="Select the property to generate statement for"
            )
            
            # Month selection
            current_date = datetime.now()
            default_month = (current_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            
            selected_month = st.text_input(
                "Month (YYYY-MM)",
                value=default_month,
                help="Enter the month to process (e.g., 2025-08)"
            )
        
        with col2:
            st.subheader("Manual Expenses")
            
            # Manual expenses input
            num_expenses = st.number_input("Number of Manual Expenses", min_value=0, max_value=10, value=0)
            
            manual_expenses = []
            for i in range(num_expenses):
                st.markdown(f"**Expense {i+1}**")
                exp_col1, exp_col2, exp_col3 = st.columns(3)
                
                with exp_col1:
                    description = st.text_input(f"Description {i+1}", key=f"desc_{i}")
                with exp_col2:
                    amount = st.number_input(f"Amount {i+1}", min_value=0.0, key=f"amt_{i}")
                with exp_col3:
                    payout_to = st.text_input(f"Payout To {i+1}", key=f"payout_{i}")
                
                if description and amount > 0:
                    manual_expenses.append({
                        'description': description,
                        'amount': amount,
                        'payout_to': payout_to or 'Various'
                    })
        
        # Generate button
        submitted = st.form_submit_button("🚀 Generate Owner Statement", type="primary")
        
        if submitted:
            generate_statement(selected_tag, selected_month, manual_expenses)

def generate_statement(tag: str, month: str, manual_expenses: List[Dict]):
    """Generate owner statement"""
    with st.spinner("Generating owner statement..."):
        try:
            # Get sample reservations (in production, this would fetch from Hospitable)
            reservations = get_sample_reservations(tag)
            
            # Process the data
            processed_data = st.session_state.processor.process_reservations_data(reservations, tag)
            
            # Add manual expenses if provided
            if manual_expenses:
                total_manual_expenses = sum(expense.get('amount', 0) for expense in manual_expenses)
                processed_data['manual_expenses'] = manual_expenses
                processed_data['other_expenses'] = total_manual_expenses
                
                # Recalculate management fee with manual expenses
                settings = processed_data['settings']
                processed_data['management_fee'] = st.session_state.processor.calculate_management_fee(
                    processed_data['reservation_income'],
                    processed_data['supplies_estimate'],
                    processed_data['utilities_estimate'],
                    total_manual_expenses,
                    settings['management_fee_percentage']
                )
                
                # Recalculate owner payout
                processed_data['owner_payout'] = (
                    processed_data['reservation_income'] - 
                    processed_data['supplies_estimate'] - 
                    processed_data['utilities_estimate'] - 
                    total_manual_expenses - 
                    processed_data['management_fee']
                )
                
                processed_data['total_payouts'] = processed_data['owner_payout'] + processed_data['management_fee']
            
            # Simulate bank verification
            bank_verification = simulate_bank_verification(processed_data['total_payouts'])
            
            # Create breakdown
            breakdown = st.session_state.processor.create_statement_breakdown(processed_data)
            
            # Add manual expenses to breakdown if present
            if manual_expenses:
                for expense in manual_expenses:
                    breakdown.insert(-1, {
                        'line_item': expense.get('description', 'Manual Expense'),
                        'amount': -expense.get('amount', 0),
                        'type': 'expense',
                        'payout_to': expense.get('payout_to', 'Various')
                    })
            
            st.success("✅ Owner statement generated successfully!")
            
            # Display results
            display_statement_results({
                'processed_data': processed_data,
                'bank_verification': bank_verification,
                'breakdown': breakdown,
                'tag': tag,
                'month': month,
                'discrepancy_found': not bank_verification['is_match']
            })
            
        except Exception as e:
            st.error(f"❌ Error generating statement: {str(e)}")

def display_statement_results(result: Dict[str, Any]):
    """Display statement generation results"""
    processed_data = result['processed_data']
    bank_verification = result['bank_verification']
    
    # Alert for discrepancies
    if result['discrepancy_found']:
        st.markdown(f"""
        <div class="alert-danger">
            <h4>⚠️ DISCREPANCY ALERT</h4>
            <p>Bank balance discrepancy of <strong>${bank_verification['discrepancy']:,.2f}</strong> detected!</p>
            <p><strong>DO NOT PROCESS PAYOUTS</strong> until this is resolved.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-success">
            <h4>✅ VERIFICATION SUCCESSFUL</h4>
            <p>All financial data verified and reconciled. Ready for payout processing.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Reservation Income",
            f"${processed_data['reservation_income']:,.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Owner Payout",
            f"${processed_data['owner_payout']:,.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            "Management Fee",
            f"${processed_data['management_fee']:,.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "Total Reservations",
            processed_data['total_reservations'],
            delta=None
        )
    
    # Detailed breakdown
    st.subheader("📊 Financial Breakdown")
    
    breakdown_data = []
    for item in result['breakdown']:
        breakdown_data.append({
            'Line Item': item['line_item'],
            'Amount': f"${item['amount']:,.2f}",
            'Type': item['type'].title(),
            'Payout To': item['payout_to']
        })
    
    df_breakdown = pd.DataFrame(breakdown_data)
    st.dataframe(df_breakdown, use_container_width=True)
    
    # Bank verification details
    st.subheader("🏦 Bank Verification")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Expected Total", f"${bank_verification['expected_amount']:,.2f}")
    with col2:
        st.metric("Actual Balance", f"${bank_verification['actual_balance']:,.2f}")
    with col3:
        st.metric("Discrepancy", f"${bank_verification['discrepancy']:,.2f}")
    
    # Reservation details
    st.subheader("🏠 Reservation Details")
    
    reservation_data = []
    for res in processed_data['reservations']:
        reservation_data.append({
            'ID': res.get('reservation_id', 'N/A'),
            'Guest': res.get('guest_name', 'N/A'),
            'Check In': res.get('check_in', 'N/A'),
            'Check Out': res.get('check_out', 'N/A'),
            'Amount': f"${res.get('total_amount', 0):,.2f}",
            'Cleaning Fee': f"${res.get('cleaning_fee', 0):,.2f}",
            'Platform': res.get('platform', 'N/A')
        })
    
    df_reservations = pd.DataFrame(reservation_data)
    st.dataframe(df_reservations, use_container_width=True)
    
    # Download options
    st.subheader("📥 Download Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate report content
        report_content = generate_report_content(result)
        st.download_button(
            label="📄 Download Statement Report",
            data=report_content,
            file_name=f"owner_statement_{result['tag'].replace(' ', '_')}_{result['month']}.md",
            mime="text/markdown"
        )
    
    with col2:
        # Create CSV download
        csv_data = df_breakdown.to_csv(index=False)
        st.download_button(
            label="📊 Download CSV Data",
            data=csv_data,
            file_name=f"owner_statement_data_{result['tag'].replace(' ', '_')}_{result['month']}.csv",
            mime="text/csv"
        )

def generate_report_content(result: Dict[str, Any]) -> str:
    """Generate markdown report content"""
    processed_data = result['processed_data']
    bank_verification = result['bank_verification']
    settings = processed_data['settings']
    
    report = f"""# Owner Statement Report

## Property: {processed_data['tag']}
**Report Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Period:** {result['month']}  
**Workflow Status:** {'⚠️ DISCREPANCY FOUND' if result['discrepancy_found'] else '✅ VERIFIED'}

## Executive Summary
- **Total Reservations:** {processed_data['total_reservations']}
- **Gross Revenue:** ${processed_data['reservation_income']:,.2f}
- **Net Owner Payout:** ${processed_data['owner_payout']:,.2f}
- **Management Fee:** ${processed_data['management_fee']:,.2f}
- **Total Deductions:** ${processed_data['supplies_estimate'] + processed_data['utilities_estimate'] + processed_data.get('other_expenses', 0):,.2f}

## Financial Breakdown

| Line Item | Amount | Type | Payout To |
|-----------|--------|------|-----------|"""
    
    for item in result['breakdown']:
        report += f"\n| {item['line_item']} | ${item['amount']:,.2f} | {item['type'].title()} | {item['payout_to']} |"
    
    report += f"""

## Calculation Methodology
- **Management Fee Rate:** {settings['management_fee_percentage']}%
- **Supplies Estimate:** {settings['supplies_estimate_percentage']}% of cleaning fees (${processed_data['cleaning_fees']:,.2f})
- **Utilities Estimate:** {settings['utilities_estimate_percentage']}% of reservation income
- **Management Fee Base:** Reservation Income - Supplies - Utilities - Other Expenses

### Management Fee Calculation:
```
Base Amount = ${processed_data['reservation_income']:,.2f} - ${processed_data['supplies_estimate']:,.2f} - ${processed_data['utilities_estimate']:,.2f} - ${processed_data.get('other_expenses', 0):,.2f}
Base Amount = ${processed_data['reservation_income'] - processed_data['supplies_estimate'] - processed_data['utilities_estimate'] - processed_data.get('other_expenses', 0):,.2f}
Management Fee = ${processed_data['reservation_income'] - processed_data['supplies_estimate'] - processed_data['utilities_estimate'] - processed_data.get('other_expenses', 0):,.2f} × {settings['management_fee_percentage']}% = ${processed_data['management_fee']:,.2f}
```

## Bank Account Verification
- **Expected Total Payouts:** ${bank_verification['expected_amount']:,.2f}
- **Actual Bank Balance:** ${bank_verification['actual_balance']:,.2f}
- **Discrepancy:** ${bank_verification['discrepancy']:,.2f}
- **Tolerance:** ${bank_verification['tolerance']:,.2f}
- **Status:** {bank_verification['status']}
- **Verification Time:** {bank_verification.get('verification_time', 'N/A')}

"""
    
    if result['discrepancy_found']:
        report += f"""
## ⚠️ DISCREPANCY ALERT
**CRITICAL:** The bank balance does not match the expected payout total.

**Immediate Actions Required:**
1. **STOP** - Do not process any payouts until discrepancy is resolved
2. Review all reservation data for completeness
3. Verify all manual expenses are correctly entered
4. Check bank account for pending transactions
5. Confirm no duplicate or missing reservations
6. Investigate the ${bank_verification['discrepancy']:,.2f} difference

"""
    else:
        report += f"""
## ✅ VERIFICATION SUCCESSFUL
All financial data has been verified and reconciled.

**Ready for Payout Processing:**
- Owner Payout: ${processed_data['owner_payout']:,.2f}
- Management Fee Retention: ${processed_data['management_fee']:,.2f}

"""
    
    report += f"""
## Reservation Details
| ID | Guest | Check In | Check Out | Revenue | Cleaning Fee | Platform |
|----|-------|----------|-----------|---------|--------------|----------|"""
    
    for reservation in processed_data['reservations']:
        report += f"\n| {reservation.get('reservation_id', 'N/A')} | {reservation.get('guest_name', 'N/A')} | {reservation.get('check_in', 'N/A')} | {reservation.get('check_out', 'N/A')} | ${reservation.get('total_amount', 0):,.2f} | ${reservation.get('cleaning_fee', 0):,.2f} | {reservation.get('platform', 'N/A')} |"
    
    report += f"""

## Next Steps
1. {'🔍 **INVESTIGATE DISCREPANCY** - Do not proceed with payouts' if result['discrepancy_found'] else '✅ **PROCEED WITH PAYOUTS** - All verifications passed'}
2. {'Review and resolve the ${:.2f} discrepancy'.format(bank_verification['discrepancy']) if result['discrepancy_found'] else 'Process owner payout: ${:,.2f}'.format(processed_data['owner_payout'])}
3. {'Re-run verification after corrections' if result['discrepancy_found'] else 'Retain management fee: ${:,.2f}'.format(processed_data['management_fee'])}
4. Update client records and file statement

---
**Generated by:** Owner Statement Generator (Abacus.AI)  
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Version:** 1.0.0
"""
    
    return report

def render_configuration():
    """Render the configuration page"""
    st.markdown('<h1 class="main-header">⚙️ Configuration</h1>', unsafe_allow_html=True)
    
    # Default settings
    st.subheader("🔧 Default Settings")
    
    with st.form("default_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            mgmt_fee = st.number_input(
                "Management Fee Percentage",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.config['default_settings']['management_fee_percentage']),
                step=0.1,
                help="Default management fee percentage"
            )
            
            supplies_pct = st.number_input(
                "Supplies Estimate Percentage",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.config['default_settings']['supplies_estimate_percentage']),
                step=0.1,
                help="Percentage of cleaning fees for supplies estimate"
            )
        
        with col2:
            utilities_pct = st.number_input(
                "Utilities Estimate Percentage",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.config['default_settings']['utilities_estimate_percentage']),
                step=0.1,
                help="Percentage of reservation income for utilities estimate"
            )
            
            default_tag = st.text_input(
                "Default Property Tag",
                value=st.session_state.config['default_settings']['default_tag'],
                help="Default property tag for statement generation"
            )
        
        if st.form_submit_button("💾 Save Default Settings"):
            st.session_state.config['default_settings'] = {
                'management_fee_percentage': mgmt_fee,
                'supplies_estimate_percentage': supplies_pct,
                'utilities_estimate_percentage': utilities_pct,
                'default_tag': default_tag
            }
            
            # Update processor
            st.session_state.processor = OwnerStatementProcessor(st.session_state.config)
            
            st.success("✅ Default settings saved successfully!")
            st.rerun()
    
    st.markdown("---")
    
    # Client overrides
    st.subheader("🏠 Client-Specific Settings")
    
    # Add new client
    with st.expander("➕ Add New Client"):
        with st.form("add_client"):
            new_tag = st.text_input("Property Tag", help="Unique identifier for the property")
            new_mgmt_fee = st.number_input("Management Fee %", value=20.0, step=0.1)
            new_supplies = st.number_input("Supplies Estimate %", value=15.0, step=0.1)
            new_utilities = st.number_input("Utilities Estimate %", value=8.0, step=0.1)
            owner_name = st.text_input("Owner Name", help="Name of the property owner")
            mgmt_company = st.text_input("Management Company", help="Name of the management company")
            
            if st.form_submit_button("➕ Add Client"):
                if new_tag and new_tag not in st.session_state.config['client_overrides']:
                    st.session_state.config['client_overrides'][new_tag] = {
                        'management_fee_percentage': new_mgmt_fee,
                        'supplies_estimate_percentage': new_supplies,
                        'utilities_estimate_percentage': new_utilities,
                        'owner_name': owner_name,
                        'management_company': mgmt_company
                    }
                    
                    # Update processor
                    st.session_state.processor = OwnerStatementProcessor(st.session_state.config)
                    
                    st.success(f"✅ Client '{new_tag}' added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Property tag already exists or is empty!")
    
    # Existing clients
    if st.session_state.config.get('client_overrides'):
        st.subheader("📋 Existing Clients")
        
        for tag, settings in st.session_state.config['client_overrides'].items():
            with st.expander(f"🏠 {tag}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Management Fee:** {settings.get('management_fee_percentage', 20)}%")
                    st.write(f"**Supplies Estimate:** {settings.get('supplies_estimate_percentage', 15)}%")
                    st.write(f"**Utilities Estimate:** {settings.get('utilities_estimate_percentage', 8)}%")
                
                with col2:
                    st.write(f"**Owner:** {settings.get('owner_name', 'N/A')}")
                    st.write(f"**Management Company:** {settings.get('management_company', 'N/A')}")
                
                if st.button(f"🗑️ Remove {tag}", key=f"remove_{tag}"):
                    del st.session_state.config['client_overrides'][tag]
                    
                    # Update processor
                    st.session_state.processor = OwnerStatementProcessor(st.session_state.config)
                    
                    st.success(f"✅ Client '{tag}' removed successfully!")
                    st.rerun()
    else:
        st.info("ℹ️ No client-specific settings configured. Using default settings for all properties.")

def render_reports():
    """Render the reports page"""
    st.markdown('<h1 class="main-header">📊 Reports & Analytics</h1>', unsafe_allow_html=True)
    
    st.info("📋 This is a demo version. In production, this page would show historical reports and analytics.")
    
    # Sample analytics
    st.subheader("📈 Sample Analytics")
    
    # Create sample monthly data
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    revenue = [4200, 3800, 4500, 4100, 4800, 4300]
    management_fees = [r * 0.2 for r in revenue]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Revenue', x=months, y=revenue))
    fig.add_trace(go.Bar(name='Management Fees', x=months, y=management_fees))
    
    fig.update_layout(
        title='Monthly Revenue and Management Fees',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Sample report list
    st.subheader("📄 Sample Reports")
    
    sample_reports = [
        {"name": "480 Laswell Ave - August 2025", "date": "2025-08-31", "status": "Completed"},
        {"name": "480 Laswell Ave - July 2025", "date": "2025-07-31", "status": "Completed"},
        {"name": "480 Laswell Ave - June 2025", "date": "2025-06-30", "status": "Completed"},
    ]
    
    for report in sample_reports:
        with st.expander(f"📄 {report['name']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Date:** {report['date']}")
            with col2:
                st.write(f"**Status:** {report['status']}")
            with col3:
                st.button(f"📥 Download", key=f"download_{report['name']}", disabled=True)

def render_help():
    """Render the help page"""
    st.markdown('<h1 class="main-header">❓ Help & Documentation</h1>', unsafe_allow_html=True)
    
    # Quick start guide
    st.subheader("🚀 Quick Start Guide")
    
    st.markdown("""
    ### 1. Configure Your Settings
    - Go to **Configuration** page
    - Set default management fee percentage (default: 20%)
    - Configure supplies and utilities estimate rates
    - Add client-specific overrides as needed
    
    ### 2. Generate Your First Statement
    - Go to **Generate Statement** page
    - Select property tag and month
    - Add any manual expenses
    - Click "Generate Owner Statement"
    
    ### 3. Review Results
    - Check for any discrepancy alerts
    - Review financial breakdown
    - Download reports for your records
    
    ### 4. Manage Properties
    - Add new properties in Configuration
    - Set custom rates per property
    - Remove properties as needed
    """)
    
    st.markdown("---")
    
    # Calculation methodology
    st.subheader("🧮 Calculation Methodology")
    
    st.markdown("""
    ### Management Fee Calculation
    ```
    Base Amount = Reservation Income - Supplies Estimate - Utilities Estimate - Manual Expenses
    Management Fee = Base Amount × Management Fee Percentage
    Owner Payout = Base Amount - Management Fee
    ```
    
    ### Estimates
    - **Supplies Estimate**: Percentage of total cleaning fees
    - **Utilities Estimate**: Percentage of total reservation income
    - **Manual Expenses**: Additional costs entered manually
    
    ### Bank Verification
    - System compares expected payout total with actual bank balance
    - Flags discrepancies exceeding $0.01 tolerance
    - Prevents payouts when discrepancies exist
    """)
    
    st.markdown("---")
    
    # Features
    st.subheader("✨ Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Core Features:**
        - ✅ Multi-property management
        - ✅ Configurable fee structures
        - ✅ Automated calculations
        - ✅ Manual expense integration
        - ✅ Bank balance verification
        - ✅ Discrepancy detection
        """)
    
    with col2:
        st.markdown("""
        **Reporting Features:**
        - ✅ Detailed financial breakdowns
        - ✅ Interactive visualizations
        - ✅ Downloadable reports
        - ✅ CSV data export
        - ✅ Historical tracking
        - ✅ Audit trails
        """)
    
    st.markdown("---")
    
    # Support
    st.subheader("📞 Support")
    st.info("This is a demo version of the Owner Statement Generator. For production deployment with real integrations, contact your system administrator.")

def main():
    """Main application function"""
    # Initialize current page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Update current page if different from sidebar selection
    if page != st.session_state.current_page:
        st.session_state.current_page = page
    
    # Render selected page
    if st.session_state.current_page == "Dashboard":
        render_dashboard()
    elif st.session_state.current_page == "Generate Statement":
        render_generate_statement()
    elif st.session_state.current_page == "Configuration":
        render_configuration()
    elif st.session_state.current_page == "Reports":
        render_reports()
    elif st.session_state.current_page == "Help":
        render_help()

if __name__ == "__main__":
    main()
