"""
Fluid Protocol Treasury Monitor - Complete Dashboard
Full version with all charts working + transaction tracking (disabled for now)
"""
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List
import json
import os
import transaction_fetcher

# Configuration
VAULT_API = "https://api.solana.fluid.io/v1/borrowing/vaults"
LENDING_API = "https://api.solana.fluid.io/v1/lending/tokens"

# Vault Mapping
VAULT_MAPPING = {
    "WSOL/USDC": {"team": "Fluid Team", "type": "supply"},
    "WSOL/USDT": {"team": "Fluid Team", "type": "supply"},
    "WSOL/USDG": {"team": "Fluid Team", "type": "supply"},
    "WSOL/EURC": {"team": "Fluid Team", "type": "supply"},  
    "WSOL/USDS": {"team": "Fluid Team", "type": "supply"},
    "WSOL/cbBTC": {"team": "Fluid Team", "type": "supply"},
    "WSOL/xBTC": {"team": "Fluid Team", "type": "supply"},
    "syrupUSDC/USDC": {"team": "Jup + Maple", "type": "borrow"},
    "JUPSOL/USDG": {"team": "USDG Team", "type": "borrow"},     
    "xBTC/USDG": {"team": "USDG Team", "type": "borrow"},
    "JitoSOL/USDG": {"team": "Jito + USDG", "type": "borrow"},
    "syrupUSDC/USDG": {"team": "Maple + USDG", "type": "borrow"},
    "LBTC/USDG": {"team": "Lombard + USDG", "type": "borrow"},
    "INF/SOL": {"team": "Sanctum", "type": "borrow"},
    "PST/USDC": {"team": "PST Team", "type": "borrow"},
    "LBTC/USDC": {"team": "Lombard + Fluid", "type": "borrow"},
}

LENDING_MAPPING = {
    "USDC": "Jupiter",
    "USDT": "Fluid Team",
    "EURC": "Fluid Team",
    "USDS": "Fluid Team",
    "USDG": "Fluid Team",
}

# Page config
st.set_page_config(
    page_title="Fluid Treasury Monitor",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .alert-high {
        background-color: #ff4444;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .alert-medium {
        background-color: #ffaa00;
        color: black;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

def fetch_vault_data() -> List[Dict]:
    """Fetch vault data from API"""
    try:
        response = requests.get(VAULT_API, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching vault data: {e}")
        return []

def fetch_lending_data() -> List[Dict]:
    """Fetch lending data from API"""
    try:
        response = requests.get(LENDING_API, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching lending data: {e}")
        return []

def process_vault_data(vaults: List[Dict]) -> pd.DataFrame:
    """Process vault data and calculate deltas"""
    rows = []
    
    for vault in vaults:
        supply_token = vault['supplyToken']['symbol']
        borrow_token = vault['borrowToken']['symbol']
        vault_pair = f"{supply_token}/{borrow_token}"
        
        supply_decimals = vault['supplyToken']['decimals']
        borrow_decimals = vault['borrowToken']['decimals']
        
        supply_delta_amount = (float(vault['totalSupply']) - float(vault['totalSupplyLiquidity'])) / (10 ** supply_decimals)
        supply_delta_usd = supply_delta_amount * float(vault['supplyToken']['price'])
        
        borrow_delta_amount = (float(vault['totalBorrow']) - float(vault['totalBorrowLiquidity'])) / (10 ** borrow_decimals)
        borrow_delta_usd = borrow_delta_amount * float(vault['borrowToken']['price'])
        
        vault_info = VAULT_MAPPING.get(vault_pair, {"team": "Unknown", "type": "unknown"})
        
        if abs(supply_delta_usd) > 100 or abs(borrow_delta_usd) > 100:
            rows.append({
                'Vault ID': vault['id'],
                'Vault Pair': vault_pair,
                'Supply Token': supply_token,
                'Borrow Token': borrow_token,
                'Supply Delta Amount': supply_delta_amount,
                'Supply Delta USD': supply_delta_usd,
                'Borrow Delta Amount': borrow_delta_amount,
                'Borrow Delta USD': borrow_delta_usd,
                'Responsible Party': vault_info['team'],
                'Incentive Type': vault_info['type'].title(),
                'Supply Token Price': float(vault['supplyToken']['price']),
                'Borrow Token Price': float(vault['borrowToken']['price'])
            })
    
    return pd.DataFrame(rows)

def process_lending_data(tokens: List[Dict]) -> pd.DataFrame:
    """Process lending data and calculate rewards"""
    rows = []
    
    for token in tokens:
        symbol = token['asset']['symbol']
        decimals = token['asset']['decimals']
        
        rewards_amount = (float(token['totalAssets']) - float(token['liquiditySupplyData']['supply'])) / (10 ** decimals)
        rewards_usd = rewards_amount * float(token['asset']['price'])
        
        responsible = LENDING_MAPPING.get(symbol, "Unknown")
        
        if abs(rewards_usd) > 100:
            rows.append({
                'Lending ID': token['id'],
                'Token': symbol,
                'Token Name': token['asset']['name'],
                'Rewards Amount': rewards_amount,
                'Rewards USD': rewards_usd,
                'Responsible Party': responsible,
                'Token Price': float(token['asset']['price']),
                'Total Assets': float(token['totalAssets']) / (10 ** decimals),
                'Liquidity Supply': float(token['liquiditySupplyData']['supply']) / (10 ** decimals)
            })
    
    return pd.DataFrame(rows)

# Initialize session state
if 'vault_data' not in st.session_state:
    st.session_state.vault_data = None
if 'lending_data' not in st.session_state:
    st.session_state.lending_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Header
st.title("💰 Fluid Protocol Treasury Monitor")
st.markdown("### Solana Outstanding Rewards Dashboard")

# Sidebar
with st.sidebar:
    st.header("Control Panel")
    
    if st.button("🔄 Fetch Fresh Data", use_container_width=True):
        with st.spinner("Fetching data from APIs..."):
            vaults = fetch_vault_data()
            lendings = fetch_lending_data()
            
            if vaults and lendings:
                st.session_state.vault_data = process_vault_data(vaults)
                st.session_state.lending_data = process_lending_data(lendings)
                st.session_state.last_update = datetime.now()
                st.success("✅ Data fetched successfully!")
            else:
                st.error("❌ Failed to fetch data")
    
    if st.session_state.last_update:
        st.info(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("---")
    st.subheader("Quick Stats")
    
    if st.session_state.vault_data is not None and st.session_state.lending_data is not None:
        vault_df = st.session_state.vault_data
        lending_df = st.session_state.lending_data
        
        total_vault_supply = vault_df['Supply Delta USD'].sum()
        total_vault_borrow = vault_df['Borrow Delta USD'].sum()
        total_lending = lending_df['Rewards USD'].sum()
        total_all = total_vault_supply + abs(total_vault_borrow) + total_lending
        
        st.metric("Total Outstanding", f"${total_all:,.0f}")
        st.metric("Vault Supply", f"${total_vault_supply:,.0f}")
        st.metric("Vault Borrow", f"${abs(total_vault_borrow):,.0f}")
        st.metric("Lending", f"${total_lending:,.0f}")

# Main content
if st.session_state.vault_data is None or st.session_state.lending_data is None:
    st.info("👈 Click 'Fetch Fresh Data' in the sidebar to load current outstanding rewards")
    st.stop()

vault_df = st.session_state.vault_data
lending_df = st.session_state.lending_data

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🏦 Vault Rewards", "💵 Lending Rewards", "💸 Transactions", "📈 Analytics"])

# Tab 1: Overview
with tab1:
    st.header("Outstanding Rewards Overview")
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_vault_supply = vault_df['Supply Delta USD'].sum()
    total_vault_borrow = abs(vault_df['Borrow Delta USD'].sum())
    total_lending = lending_df['Rewards USD'].sum()
    total_all = total_vault_supply + total_vault_borrow + total_lending
    
    with col1:
        st.metric("Total Outstanding", f"${total_all:,.0f}")
    with col2:
        st.metric("Vault Supply Rewards", f"${total_vault_supply:,.0f}", 
                 help="SOL collateral incentives")
    with col3:
        st.metric("Vault Borrow Discounts", f"${total_vault_borrow:,.0f}",
                 help="Interest rate discounts")
    with col4:
        st.metric("Lending Rewards", f"${total_lending:,.0f}")
    
    st.markdown("---")
    
    # Current Treasury Balance Section
    st.subheader("💰 Current Treasury Balance")
    
    # Fetch current balance using Solscan API (CORRECTED)
    try:
        balance_url = "https://pro-api.solscan.io/v2.0/account/token-accounts"
        headers = {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NTQyOTkxNzA4MzMsImVtYWlsIjoidG9vbHNAcmFjY29vbnMuZGV2IiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzU0Mjk5MTcwfQ.OjCC76Qy4IMVqzA6fXBI3uDQ2F7RjskOQATRztSsS_o"}
        params = {
            "address": "Cvnta5ecoiCgNbLEXYm6kvhJMmRv3JM3ksKgTLVPg4hk",
            "type": "token",
            "page": 1,
            "page_size": 20
        }
        
        response = requests.get(balance_url, headers=headers, params=params, timeout=10)
        balance_data = response.json()
        
        if balance_data.get('success'):
            token_accounts = balance_data.get('data', [])
            metadata = balance_data.get('metadata', {})
            tokens_meta = metadata.get('tokens', {})
            
            # Get prices from Fluid API
            try:
                vaults_response = requests.get(VAULT_API, timeout=10)
                vaults = vaults_response.json()
                
                # Extract prices
                prices = {}
                for vault in vaults:
                    supply_token = vault.get('supplyToken', {})
                    borrow_token = vault.get('borrowToken', {})
                    
                    if supply_token.get('symbol'):
                        prices[supply_token['symbol']] = float(supply_token.get('price', 0))
                    if borrow_token.get('symbol'):
                        prices[borrow_token['symbol']] = float(borrow_token.get('price', 0))
                
                # Ensure we have SOL price
                sol_price = prices.get('WSOL', prices.get('SOL', 150.0))
            except:
                sol_price = 150.0
                prices = {}
            
            # Process balances
            balances = []
            total_value = 0
            
            for account in token_accounts:
                token_address = account.get('token_address', '')
                amount_raw = account.get('amount', 0)
                decimals = account.get('token_decimals', 6)
                
                # Get token metadata
                token_info = tokens_meta.get(token_address, {})
                token_symbol = token_info.get('token_symbol', 'UNKNOWN')
                
                # Calculate real amount
                amount = amount_raw / (10 ** decimals)
                
                if amount > 0:  # Only show non-zero balances
                    # Calculate USD value
                    value_usd = 0
                    
                    # Skip MNDE and JTO (governance tokens)
                    if token_symbol in ['MNDE', 'JTO']:
                        value_usd = 0
                    # Stablecoins
                    elif token_symbol in ['USDC', 'USDT', 'USDS', 'USDG']:
                        value_usd = amount * 1.0
                    # SOL/WSOL
                    elif token_symbol in ['SOL', 'WSOL']:
                        value_usd = amount * sol_price
                    # EURC - from Fluid API
                    elif token_symbol == 'EURC':
                        value_usd = amount * prices.get('EURC', 1.0)
                    # syrupUSDC - from Fluid API
                    elif token_symbol == 'syrupUSDC':
                        value_usd = amount * prices.get('syrupUSDC', 1.0)
                    else:
                        # Try to get from Fluid API
                        value_usd = amount * prices.get(token_symbol, 0)
                    
                    total_value += value_usd
                    
                    balances.append({
                        'Token': token_symbol,
                        'Amount': amount,
                        'Value USD': value_usd
                    })
            
            if balances:
                # Sort by value
                balances_df = pd.DataFrame(balances).sort_values('Value USD', ascending=False)
                
                # Show total
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Treasury Value", f"${total_value:,.0f}")
                with col2:
                    # Count only tokens with USD value
                    meaningful_tokens = len(balances_df[balances_df['Value USD'] > 0])
                    st.metric("Number of Tokens", f"{meaningful_tokens} (valued)")
                with col3:
                    # Largest holding (excluding zero-value tokens)
                    valued_df = balances_df[balances_df['Value USD'] > 0]
                    if not valued_df.empty:
                        largest = valued_df.iloc[0]
                        st.metric("Largest Holding", f"{largest['Token']}: ${largest['Value USD']:,.0f}")
                    else:
                        st.metric("Largest Holding", "N/A")
                
                # Show balance table
                st.dataframe(
                    balances_df.style.format({
                        'Amount': '{:,.4f}',
                        'Value USD': '${:,.2f}'
                    }),
                    use_container_width=True,
                    height=300
                )
                
                # Charts only for valued tokens
                valued_df = balances_df[balances_df['Value USD'] > 1000].copy()
                
                if not valued_df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Pie chart
                        fig = px.pie(
                            valued_df,
                            values='Value USD',
                            names='Token',
                            title='Treasury Composition by Value (>$1k)'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Bar chart
                        fig = px.bar(
                            valued_df.head(10),
                            x='Token',
                            y='Value USD',
                            title='Top Holdings by Value',
                            color='Token'
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No significant token holdings (>$1k) to chart")
            else:
                st.info("No token balances found")
        else:
            st.warning("Could not fetch treasury balance")
    
    except Exception as e:
        st.warning(f"Could not fetch treasury balance: {str(e)}")
    
    st.markdown("---")

    # ADD THIS SECTION TO OVERVIEW TAB
# Insert AFTER the treasury balance section and BEFORE rebalance alerts

    st.markdown("---")
    
    # Pending Rewards Summary by Token
    st.subheader("🔔 Pending Rewards Summary (By Token)")
    
    st.markdown("""
    **Total tokens required for rebalancing**, grouped by token type.
    """)
    
    try:
        # Fetch vaults and lending data
        vaults_response = requests.get(VAULT_API, timeout=10)
        lending_response = requests.get(LENDING_API, timeout=10)
        vaults = vaults_response.json()
        lending_tokens = lending_response.json()
        
        # Initialize accumulators
        pending_rewards = {
            'USDC': 0,
            'USDG': 0,
            'SOL': 0,
            'EURC': 0,
            'USDS': 0,
            'USDT': 0
        }
        
        # Process Vaults
        for vault in vaults:
            vault_name = f"{vault['supplyToken']['symbol']}/{vault['borrowToken']['symbol']}"
            
            supply_symbol = vault['supplyToken']['symbol']
            borrow_symbol = vault['borrowToken']['symbol']
            supply_decimals = vault['supplyToken']['decimals']
            borrow_decimals = vault['borrowToken']['decimals']
            
            # Supply rewards (SOL vaults)
            if supply_symbol == 'WSOL':
                total_supply = float(vault.get('totalSupply', 0))
                total_supply_liquidity = float(vault.get('totalSupplyLiquidity', 0))
                supply_delta = (total_supply - total_supply_liquidity) / (10 ** supply_decimals)
                
                if supply_delta > 0:
                    pending_rewards['SOL'] += supply_delta
            
            # Borrow rewards
            total_borrow = float(vault.get('totalBorrow', 0))
            total_borrow_liquidity = float(vault.get('totalBorrowLiquidity', 0))
            borrow_delta = (total_borrow - total_borrow_liquidity) / (10 ** borrow_decimals)
            
            if borrow_delta > 0:
                # Determine which token bucket
                if borrow_symbol == 'USDC':
                    pending_rewards['USDC'] += borrow_delta
                elif borrow_symbol == 'USDG':
                    pending_rewards['USDG'] += borrow_delta
                elif borrow_symbol == 'EURC':
                    pending_rewards['EURC'] += borrow_delta
                elif borrow_symbol == 'SOL':
                    pending_rewards['SOL'] += borrow_delta
        
        # Process Lending
        for token in lending_tokens:
            symbol = token['asset']['symbol']
            decimals = token['asset']['decimals']
            
            total_assets = float(token.get('totalAssets', 0))
            liquidity_supply = float(token.get('liquiditySupplyData', {}).get('supply', 0))
            
            lending_delta = (total_assets - liquidity_supply) / (10 ** decimals)
            
            if lending_delta > 0:
                if symbol == 'USDC':
                    pending_rewards['USDC'] += lending_delta
                elif symbol == 'USDG':
                    pending_rewards['USDG'] += lending_delta
                elif symbol == 'USDT':
                    pending_rewards['USDT'] += lending_delta
                elif symbol == 'EURC':
                    pending_rewards['EURC'] += lending_delta
                elif symbol == 'USDS':
                    pending_rewards['USDS'] += lending_delta
        
        # Create summary dataframe
        summary_data = []
        
        # Get SOL price for USD value
        sol_price = 150.0
        for vault in vaults:
            if vault.get('supplyToken', {}).get('symbol') == 'WSOL':
                sol_price = float(vault['supplyToken']['price'])
                break
        
        for token, amount in pending_rewards.items():
            if amount > 0:
                # Calculate USD value
                if token == 'SOL':
                    usd_value = amount * sol_price
                else:
                    # All others are stablecoins or close to $1
                    usd_value = amount * 1.0
                
                summary_data.append({
                    'Token': token,
                    'Amount Required': amount,
                    'USD Value': usd_value
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values('USD Value', ascending=False)
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            total_usd = summary_df['USD Value'].sum()
            
            with col1:
                st.metric("Total Pending (USD)", f"${total_usd:,.0f}")
            with col2:
                st.metric("Tokens to Rebalance", len(summary_df))
            with col3:
                largest = summary_df.iloc[0]
                st.metric("Largest Need", f"{largest['Token']}: ${largest['USD Value']:,.0f}")
            
            # Display table
            st.dataframe(
                summary_df.style.format({
                    'Amount Required': '{:,.2f}',
                    'USD Value': '${:,.2f}'
                }),
                use_container_width=True
            )
            
            # Bar chart
            fig = px.bar(
                summary_df,
                x='Token',
                y='USD Value',
                title='Pending Rewards by Token',
                color='Token',
                labels={'USD Value': 'USD Value Required'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.success("✅ No pending rewards to rebalance!")
    
    except Exception as e:
        st.error(f"Error calculating pending rewards: {str(e)}")
    
    st.markdown("---")
    
    # Alerts
    st.subheader("⚠️ Rebalance Alerts")
    
    high_vaults = vault_df[vault_df['Supply Delta USD'] > 300000]
    high_borrows = vault_df[vault_df['Borrow Delta USD'].abs() > 100000]
    high_lending = lending_df[lending_df['Rewards USD'] > 300000]
    
    if len(high_vaults) > 0:
        st.markdown("### 🔴 High Supply Rewards (>$300k)")
        for _, row in high_vaults.iterrows():
            st.markdown(f"""
            <div class="alert-high">
                <strong>{row['Vault Pair']}</strong> - ${row['Supply Delta USD']:,.0f}<br>
                Team: {row['Responsible Party']} | Amount: {row['Supply Delta Amount']:,.2f} {row['Supply Token']}
            </div>
            """, unsafe_allow_html=True)
    
    if len(high_borrows) > 0:
        st.markdown("### 🟡 High Borrow Discounts (>$100k)")
        for _, row in high_borrows.iterrows():
            st.markdown(f"""
            <div class="alert-medium">
                <strong>{row['Vault Pair']}</strong> - ${abs(row['Borrow Delta USD']):,.0f}<br>
                Team: {row['Responsible Party']} | Amount: {abs(row['Borrow Delta Amount']):,.2f} {row['Borrow Token']}
            </div>
            """, unsafe_allow_html=True)
    
    if len(high_lending) > 0:
        st.markdown("### 🔴 High Lending Rewards (>$300k)")
        for _, row in high_lending.iterrows():
            st.markdown(f"""
            <div class="alert-high">
                <strong>{row['Token']}</strong> - ${row['Rewards USD']:,.0f}<br>
                Team: {row['Responsible Party']} | Amount: {row['Rewards Amount']:,.2f} {row['Token']}
            </div>
            """, unsafe_allow_html=True)
    
    if len(high_vaults) == 0 and len(high_borrows) == 0 and len(high_lending) == 0:
        st.success("✅ No urgent rebalancing needed")
    
    st.markdown("---")
    
    # Breakdown by team
    st.subheader("Breakdown by Responsible Party")
    
    # Combine data
    vault_supply_by_team = vault_df.groupby('Responsible Party')['Supply Delta USD'].sum()
    vault_borrow_by_team = vault_df.groupby('Responsible Party')['Borrow Delta USD'].apply(lambda x: abs(x).sum())
    lending_by_team = lending_df.groupby('Responsible Party')['Rewards USD'].sum()
    
    team_summary = pd.DataFrame({
        'Vault Supply': vault_supply_by_team,
        'Vault Borrow': vault_borrow_by_team,
        'Lending': lending_by_team
    }).fillna(0)
    
    team_summary['Total'] = team_summary.sum(axis=1)
    team_summary = team_summary.sort_values('Total', ascending=False)
    
    fig = px.bar(
        team_summary.reset_index(),
        x='Responsible Party',
        y=['Vault Supply', 'Vault Borrow', 'Lending'],
        title='Outstanding Rewards by Team',
        barmode='stack',
        labels={'value': 'USD', 'variable': 'Type'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    col1, col2 = st.columns(2)
    with col1:
        csv = pd.concat([
            vault_df.assign(Type='Vault'),
            lending_df.assign(Type='Lending')
        ]).to_csv(index=False)
        st.download_button(
            "📥 Download All Data CSV",
            csv,
            f"fluid_outstanding_rewards_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )

# Tab 2: Vault Rewards
with tab2:
    st.header("Vault Outstanding Rewards")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        show_supply = st.checkbox("Show Supply Rewards", value=True)
    with col2:
        show_borrow = st.checkbox("Show Borrow Discounts", value=True)
    with col3:
        team_filter = st.multiselect("Filter by Team", 
                                     options=vault_df['Responsible Party'].unique(),
                                     default=vault_df['Responsible Party'].unique())
    
    # Filter data
    filtered_df = vault_df[vault_df['Responsible Party'].isin(team_filter)]
    
    if show_supply:
        st.subheader("💎 Supply Rewards (Collateral Incentives)")
        supply_df = filtered_df[filtered_df['Supply Delta USD'] > 100].copy()
        
        if not supply_df.empty:
            st.dataframe(
                supply_df[['Vault Pair', 'Supply Delta Amount', 'Supply Delta USD', 
                          'Responsible Party', 'Supply Token Price']].style.format({
                    'Supply Delta Amount': '{:,.4f}',
                    'Supply Delta USD': '${:,.2f}',
                    'Supply Token Price': '${:,.4f}'
                }),
                use_container_width=True
            )
            
            fig = px.bar(
                supply_df,
                x='Vault Pair',
                y='Supply Delta USD',
                color='Responsible Party',
                title='Supply Rewards by Vault'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant supply rewards")
    
    if show_borrow:
        st.subheader("📉 Borrow Discounts (Interest Rate Subsidies)")
        borrow_df = filtered_df[filtered_df['Borrow Delta USD'].abs() > 100].copy()
        
        if not borrow_df.empty:
            st.dataframe(
                borrow_df[['Vault Pair', 'Borrow Delta Amount', 'Borrow Delta USD',
                          'Responsible Party', 'Borrow Token Price']].style.format({
                    'Borrow Delta Amount': '{:,.4f}',
                    'Borrow Delta USD': '${:,.2f}',
                    'Borrow Token Price': '${:,.4f}'
                }),
                use_container_width=True
            )
            
            fig = px.bar(
                borrow_df,
                x='Vault Pair',
                y='Borrow Delta USD',
                color='Responsible Party',
                title='Borrow Discounts by Vault'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant borrow discounts")
    
    # Export
    csv = vault_df.to_csv(index=False)
    st.download_button(
        "📥 Download Vault Data CSV",
        csv,
        f"vault_rewards_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

# Tab 3: Lending Rewards
with tab3:
    st.header("Lending Outstanding Rewards")
    
    # Filter by team
    team_filter = st.multiselect("Filter by Team",
                                 options=lending_df['Responsible Party'].unique(),
                                 default=lending_df['Responsible Party'].unique(),
                                 key="lending_filter")
    
    filtered_lending = lending_df[lending_df['Responsible Party'].isin(team_filter)]
    
    # Display table
    st.dataframe(
        filtered_lending[['Token', 'Token Name', 'Rewards Amount', 'Rewards USD',
                         'Responsible Party', 'Token Price']].style.format({
            'Rewards Amount': '{:,.4f}',
            'Rewards USD': '${:,.2f}',
            'Token Price': '${:,.6f}'
        }),
        use_container_width=True
    )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(
            filtered_lending,
            values='Rewards USD',
            names='Token',
            title='Lending Rewards by Token'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            filtered_lending,
            x='Token',
            y='Rewards USD',
            color='Responsible Party',
            title='Lending Rewards by Responsible Party'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Export
    csv = lending_df.to_csv(index=False)
    st.download_button(
        "📥 Download Lending Data CSV",
        csv,
        f"lending_rewards_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

# Tab 4: Transactions
with tab4:
    st.header("💸 Treasury Transactions")
    
    st.markdown("""
    **Track all inflows and outflows to/from treasury**
    - Inflows: Money coming TO treasury (tagged by team)
    - Outflows: Money going FROM treasury (rebalances)
    - Minimum: $1,000 USD
    - Cached for fast loading
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Fetch Transactions", use_container_width=True):
            with st.spinner("Fetching from Solscan..."):
                progress_container = st.empty()
                
                def progress_callback(msg):
                    progress_container.info(msg)
                
                transactions, success, error = transaction_fetcher.fetch_all_transactions(progress_callback)
                
                if success:
                    st.session_state.transactions = transactions
                    progress_container.success(f"✅ Loaded {len(transactions)} transactions")
                else:
                    progress_container.error(f"❌ {error}")
    
    with col2:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            if transaction_fetcher.clear_cache():
                st.session_state.transactions = None
                st.success("Cache cleared! Click 'Fetch Transactions' to reload.")
            else:
                st.info("No cache to clear")
    
    # Display transactions if loaded
    if 'transactions' in st.session_state and st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)
        
        st.markdown("---")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        inflows = df[df['type'] == 'Inflow']
        outflows = df[df['type'] == 'Outflow']
        
        with col1:
            st.metric("Total Transactions", len(df))
        with col2:
            st.metric("Inflows", len(inflows))
        with col3:
            st.metric("Outflows", len(outflows))
        with col4:
            total_value = df['value_usd'].sum()
            st.metric("Total Volume", f"${total_value:,.0f}")
        
        st.markdown("---")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            type_filter = st.multiselect(
                "Type",
                options=['Inflow', 'Outflow'],
                default=['Inflow', 'Outflow']
            )
        
        with col2:
            token_filter = st.multiselect(
                "Token",
                options=sorted(df['token'].unique().tolist()),
                default=df['token'].unique().tolist()
            )
        
        with col3:
            team_filter = st.multiselect(
                "Team",
                options=sorted(df['team'].unique().tolist()),
                default=df['team'].unique().tolist()
            )
        
        # Apply filters
        filtered = df[
            (df['type'].isin(type_filter)) &
            (df['token'].isin(token_filter)) &
            (df['team'].isin(team_filter))
        ]
        
        # Display table
        st.subheader(f"📋 Transactions ({len(filtered)} shown)")
        
        display_df = filtered[['timestamp', 'type', 'token', 'amount', 'value_usd', 'team', 'signature']].copy()
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['signature'] = display_df['signature'].apply(lambda x: x[:8] + '...')
        
        st.dataframe(
            display_df.style.format({
                'amount': '{:,.4f}',
                'value_usd': '${:,.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        st.markdown("---")
        
        # Charts Section
        st.subheader("📊 Transaction Analytics")
        
        # Row 1: Inflows by Team ($ Value) + Outflows by Token
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Team Inflows by $ Value")
            inflow_data = filtered[filtered['type'] == 'Inflow']
            
            if not inflow_data.empty:
                team_inflow_value = inflow_data.groupby('team')['value_usd'].sum().reset_index()
                team_inflow_value = team_inflow_value.sort_values('value_usd', ascending=False)
                
                fig = px.bar(
                    team_inflow_value,
                    x='team',
                    y='value_usd',
                    title='Total Inflow Value by Team',
                    labels={'value_usd': 'USD Value', 'team': 'Team'},
                    color='team'
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Show totals
                st.caption(f"**Total Inflows: ${team_inflow_value['value_usd'].sum():,.0f}**")
            else:
                st.info("No inflows to display")
        
        with col2:
            st.markdown("### 📤 Outflows by Token")
            outflow_data = filtered[filtered['type'] == 'Outflow']
            
            if not outflow_data.empty:
                token_outflows = outflow_data.groupby('token').agg({
                    'value_usd': 'sum',
                    'signature': 'count'
                }).reset_index()
                token_outflows.columns = ['token', 'total_value', 'count']
                token_outflows = token_outflows.sort_values('total_value', ascending=False)
                
                fig = px.bar(
                    token_outflows,
                    x='token',
                    y='total_value',
                    title='Total Outflow Value by Token',
                    labels={'total_value': 'USD Value', 'token': 'Token'},
                    color='token',
                    hover_data={'count': True}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Show totals
                st.caption(f"**Total Outflows: ${token_outflows['total_value'].sum():,.0f}**")
            else:
                st.info("No outflows to display")
        
        # Row 2: Outflow Timeline
        st.markdown("### 📈 Outflow Timeline by Token")
        if not outflow_data.empty:
            outflow_timeline = outflow_data.copy()
            outflow_timeline['date'] = outflow_timeline['timestamp'].dt.date
            
            timeline_data = outflow_timeline.groupby(['date', 'token'])['value_usd'].sum().reset_index()
            
            fig = px.line(
                timeline_data,
                x='date',
                y='value_usd',
                color='token',
                title='Outflow Value Over Time',
                labels={'value_usd': 'USD Value', 'date': 'Date'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outflows to display")
        
        # Export
        st.markdown("---")
        csv = filtered.to_csv(index=False)
        st.download_button(
            "📥 Download Transactions CSV",
            csv,
            f"treasury_transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    else:
        st.info("👆 Click 'Fetch Transactions' to load transaction history")

# Tab 5: Analytics 
with tab5:

    st.header("Analytics & Insights")
    
    # Time series would go here if we had historical data
    st.subheader("Current Snapshot Analysis")
    
    # Top rebalancing priorities
    st.markdown("### 🎯 Top Rebalancing Priorities")
    
    priorities = []
    
    for _, row in vault_df.iterrows():
        if row['Supply Delta USD'] > 100000:
            priorities.append({
                'Type': 'Vault Supply',
                'Item': row['Vault Pair'],
                'Amount USD': row['Supply Delta USD'],
                'Team': row['Responsible Party'],
                'Priority': 'High' if row['Supply Delta USD'] > 300000 else 'Medium'
            })
        if abs(row['Borrow Delta USD']) > 50000:
            priorities.append({
                'Type': 'Vault Borrow',
                'Item': row['Vault Pair'],
                'Amount USD': abs(row['Borrow Delta USD']),
                'Team': row['Responsible Party'],
                'Priority': 'High' if abs(row['Borrow Delta USD']) > 100000 else 'Medium'
            })
    
    for _, row in lending_df.iterrows():
        if row['Rewards USD'] > 100000:
            priorities.append({
                'Type': 'Lending',
                'Item': row['Token'],
                'Amount USD': row['Rewards USD'],
                'Team': row['Responsible Party'],
                'Priority': 'High' if row['Rewards USD'] > 300000 else 'Medium'
            })
    
    if priorities:
        priority_df = pd.DataFrame(priorities).sort_values('Amount USD', ascending=False)
        st.dataframe(
            priority_df.style.format({'Amount USD': '${:,.0f}'}),
            use_container_width=True
        )
    else:
        st.success("✅ No high-priority rebalancing needed")
    
    # Team workload
    st.markdown("### 👥 Team Workload")
    
    team_workload = pd.concat([
        vault_df.groupby('Responsible Party').agg({
            'Supply Delta USD': 'sum',
            'Borrow Delta USD': lambda x: abs(x).sum()
        }),
        lending_df.groupby('Responsible Party')['Rewards USD'].sum()
    ], axis=1).fillna(0)
    
    team_workload.columns = ['Vault Supply', 'Vault Borrow', 'Lending']
    team_workload['Total'] = team_workload.sum(axis=1)
    team_workload = team_workload.sort_values('Total', ascending=False)
    
    fig = go.Figure(data=[
        go.Bar(name='Vault Supply', x=team_workload.index, y=team_workload['Vault Supply']),
        go.Bar(name='Vault Borrow', x=team_workload.index, y=team_workload['Vault Borrow']),
        go.Bar(name='Lending', x=team_workload.index, y=team_workload['Lending'])
    ])
    fig.update_layout(barmode='stack', title='Outstanding Rewards by Team')
    st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    Fluid Protocol Treasury Monitor | Data fetched from Fluid Solana API | Last updated: {}
</div>
""".format(st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S') if st.session_state.last_update else 'Never'), 
unsafe_allow_html=True)
