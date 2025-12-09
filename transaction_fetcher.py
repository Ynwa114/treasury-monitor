"""
Treasury Transaction Fetcher using Solscan API
Clean, simple, and it actually works!
"""

import requests
import pandas as pd
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY')
SOLSCAN_API_URL = "https://pro-api.solscan.io/v2.0/account/transfer"
VAULT_API = "https://api.solana.fluid.io/v1/borrowing/vaults"
TREASURY_ADDRESS = "Cvnta5ecoiCgNbLEXYm6kvhJMmRv3JM3ksKgTLVPg4hk"
MIN_VALUE_USD = 1000
CACHE_FILE = "transaction_cache.json"

# Team address tags
ADDRESS_TAGS = {
    "5AZYLkiU4SPYDeRMcPbPRPmiz2Ny85jWFeV4xmQsVBNo": "Fluid Team",
    "HUBLSmfDxXxxzgg4KM6Q5onHVwBG5KeKjeA2BnvE5D9r": "Fluid Team",
    "7b1zZUuae2F56e66GqpkKe1Tq1BK2ePRRuGGr8ahe2JB": "JUP Team",
    "FH9bgRZrEGFA1d4859wSBdNnHgtU5ZDqFUPccHDnYQ3p": "Maple",
    "DVBfCpHoAtVgcVLFHyUgXaWg5ZaKU8CkekXu23ZD4iod": "Gauntlet",
    "fr6yQkDmWy6R6pecbUsxXaw6EvRJznZ2HsK5frQgud8": "USDG Team",
    "8sjM83a4u2M8YZYshLGKzYxh1VHFfbgtaytwaoEg4bUJ": "Jito Team",
    "8JmDPG5BFQ6gpUPJV9xBixYJLqTKCSNotkXksTmNsQfj": "Sky Team",
    "62SJTxjWbyaPei1HPW9mFX7KMYCEp7Z9zwiL4hGa8WQv": "LBTC Team",
    "EeQmNqm1RcQnee8LTyx6ccVG9FnR8TezQuw2JXq2LC1T": "Sanctum INF Team",
    "41zCUJsKk6cMB94DDtm99qWmyMZfp4GkAhhuz4xTwePu": "PST Team",
    "JANAjsZKJhtHF9PUF8cwjVp5oQjdcHYiGiFgc8TWQjp2": "Binance Campaign",
    "3ssDYFbTpACkshGeYHMBovxB4aE2G6fbZNeVChi85J1k": "Binance Campaign",
    "7s1da8DduuBFqGra5bJBjpnvL5E9mGzCuMk1Qkh4or2Z": "Liquidity Layer",
}


def get_sol_price():
    """Get SOL price from Fluid API"""
    try:
        response = requests.get(VAULT_API, timeout=10)
        vaults = response.json()
        
        # Find a vault with WSOL as supply token
        for vault in vaults:
            if vault.get('supplyToken', {}).get('symbol') == 'WSOL':
                price = float(vault['supplyToken']['price'])
                return price
        
        return 150.0  # Fallback price
    except:
        return 150.0  # Fallback price


def load_from_cache():
    """Load from cache if exists"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                transactions = cache_data['transactions']
                
                # Convert timestamp strings back to datetime objects
                for tx in transactions:
                    if isinstance(tx['timestamp'], str):
                        tx['timestamp'] = datetime.fromisoformat(tx['timestamp'])
                
                return transactions, cache_data['last_updated']
        except:
            return None, None
    return None, None


def save_to_cache(transactions):
    """Save to cache"""
    # Convert datetime objects to strings for JSON serialization
    transactions_serializable = []
    for tx in transactions:
        tx_copy = tx.copy()
        if isinstance(tx_copy['timestamp'], datetime):
            tx_copy['timestamp'] = tx_copy['timestamp'].isoformat()
        transactions_serializable.append(tx_copy)
    
    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "transactions": transactions_serializable
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f)


def fetch_from_solscan(page=1, page_size=40):
    """
    Fetch transactions from Solscan API
    Returns: (data_list, success, error_message)
    """
    try:
        if not SOLSCAN_API_KEY:
            return [], {}, False, "SOLSCAN_API_KEY not found in environment variables"
        
        url = f"{SOLSCAN_API_URL}?address={TREASURY_ADDRESS}&page={page}&page_size={page_size}&sort_by=block_time&sort_order=desc"
        headers = {"token": SOLSCAN_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get('success'):
            return [], {}, False, "API returned success=false"
        
        data = result.get('data', [])
        metadata = result.get('metadata', {})
        
        return data, metadata, True, None
        
    except Exception as e:
        return [], {}, False, str(e)


def process_transactions(raw_data, metadata):
    """
    Process raw Solscan data into clean format
    """
    processed = []
    tokens_meta = metadata.get('tokens', {})
    
    # Get SOL price once
    sol_price = get_sol_price()
    
    for tx in raw_data:
        # Get flow direction
        flow = tx.get('flow', '')  # 'in' or 'out'
        tx_type = 'Inflow' if flow == 'in' else 'Outflow'
        
        # Get counterparty (who we're dealing with)
        if flow == 'in':
            counterparty = tx.get('from_address', '')
        else:
            counterparty = tx.get('to_address', '')
        
        # Tag the team
        team = ADDRESS_TAGS.get(counterparty, "Unknown")
        
        # Get token info
        token_address = tx.get('token_address', '')
        token_info = tokens_meta.get(token_address, {})
        token_symbol = token_info.get('token_symbol', 'UNKNOWN')
        
        # Calculate real amount (divide by decimals)
        amount_raw = tx.get('amount', 0)
        decimals = tx.get('token_decimals', 6)
        amount = amount_raw / (10 ** decimals)
        
        # Calculate USD value
        if token_symbol in ['USDC', 'USDT', 'USDS', 'USDG', 'EURC']:
            # Stablecoins = $1
            value_usd = amount * 1.0
        elif token_symbol in ['SOL', 'WSOL']:
            # Use SOL price from Fluid API
            value_usd = amount * sol_price
        else:
            # Use Solscan's value if available
            value_usd = tx.get('value', 0)
        
        # Skip if below minimum value
        if value_usd < MIN_VALUE_USD:
            continue
        
        # Get timestamp
        timestamp = datetime.fromisoformat(tx.get('time', '').replace('Z', '+00:00'))
        
        processed.append({
            'signature': tx.get('trans_id', ''),
            'timestamp': timestamp,
            'type': tx_type,
            'token': token_symbol,
            'amount': amount,
            'value_usd': value_usd,
            'counterparty': counterparty,
            'team': team,
            'block_id': tx.get('block_id', 0)
        })
    
    return processed


def fetch_all_transactions(progress_callback=None, max_pages=5):
    """
    Main fetch function
    Returns: (transactions_list, success, error_message)
    """
    try:
        # Check cache first
        cached, last_updated = load_from_cache()
        if cached:
            if progress_callback:
                progress_callback(f"📂 Loaded {len(cached)} transactions from cache (Updated: {last_updated})")
            return cached, True, None
        
        if progress_callback:
            progress_callback("🔄 Fetching from Solscan API...")
        
        all_transactions = []
        
        # Fetch multiple pages
        for page in range(1, max_pages + 1):
            if progress_callback:
                progress_callback(f"Fetching page {page}/{max_pages}...")
            
            raw_data, metadata, success, error = fetch_from_solscan(page=page, page_size=40)
            
            if not success:
                return [], False, error
            
            if not raw_data:
                # No more data
                break
            
            # Process this page
            processed = process_transactions(raw_data, metadata)
            all_transactions.extend(processed)
        
        if progress_callback:
            progress_callback(f"✅ Fetched {len(all_transactions)} transactions (>${MIN_VALUE_USD} USD)")
        
        # Save to cache
        save_to_cache(all_transactions)
        
        return all_transactions, True, None
        
    except Exception as e:
        error_msg = str(e)
        if progress_callback:
            progress_callback(f"❌ Error: {error_msg}")
        return [], False, error_msg


def clear_cache():
    """Clear the cache"""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        return True
    return False


def get_transactions_dataframe():
    """
    Get transactions as DataFrame
    Returns: (dataframe, success, error_message)
    """
    transactions, success, error = fetch_all_transactions()
    
    if not success:
        return pd.DataFrame(), False, error
    
    if not transactions:
        return pd.DataFrame(), True, "No transactions found"
    
    df = pd.DataFrame(transactions)
    return df, True, None


if __name__ == "__main__":
    # Test the module
    print("Testing Solscan transaction fetcher...")
    
    def print_progress(msg):
        print(msg)
    
    transactions, success, error = fetch_all_transactions(print_progress, max_pages=3)
    
    if success:
        print(f"\n✅ Success! Fetched {len(transactions)} transactions")
        
        if transactions:
            print(f"\nFirst transaction:")
            print(json.dumps(transactions[0], indent=2, default=str))
            
            # Show summary
            df = pd.DataFrame(transactions)
            print(f"\n📊 Summary:")
            print(f"Total transactions: {len(df)}")
            print(f"Inflows: {len(df[df['type']=='Inflow'])}")
            print(f"Outflows: {len(df[df['type']=='Outflow'])}")
            print(f"\nBy team:")
            print(df['team'].value_counts())
            print(f"\nBy token:")
            print(df['token'].value_counts())
    else:
        print(f"\n❌ Error: {error}")