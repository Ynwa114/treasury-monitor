"""
Complete configuration for Fluid Protocol Treasury Monitor
Includes all vault and lending token mappings
"""

from datetime import datetime

# API Endpoints
VAULT_API = "https://api.solana.fluid.io/v1/borrowing/vaults"
LENDING_API = "https://api.solana.fluid.io/v1/lending/tokens"

# Treasury Configuration
TREASURY_ADDRESS = "Cvnta5ecoiCgNbLEXYm6kvhJMmRv3JM3ksKgTLVPg4hk"
START_DATE = datetime(2025, 8, 19)

# Vault Responsible Party Mapping
# Maps vault pairs to responsible teams
VAULT_MAPPING = {
    # Fluid Team - SOL collateral vaults (Supply Delta)
    "WSOL/USDC": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/USDT": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/USDG": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/EURC": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/USDS": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/cbBTC": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    "WSOL/xBTC": {"team": "Fluid Team", "type": "supply", "description": "SOL collateral incentives"},
    
    # Jup + Maple - Borrow Delta (IR discounts)
    "syrupUSDC/USDC": {"team": "Jup + Maple", "type": "borrow", "description": "Interest rate discounts"},
    
    # USDG Team vaults - Borrow Delta (IR discounts)
    "JUPSOL/USDG": {"team": "USDG Team", "type": "borrow", "description": "Interest rate discounts"},
    "WSOL/USDG": {"team": "USDG Team", "type": "borrow", "description": "Interest rate discounts"},
    "xBTC/USDG": {"team": "USDG Team", "type": "borrow", "description": "Interest rate discounts"},
    
    # Jito + USDG
    "JitoSOL/USDG": {"team": "Jito + USDG", "type": "borrow", "description": "Interest rate discounts"},
    
    # Maple + USDG
    "syrupUSDC/USDG": {"team": "Maple + USDG", "type": "borrow", "description": "Interest rate discounts"},
    
    # Lombard + USDG
    "LBTC/USDG": {"team": "Lombard + USDG", "type": "borrow", "description": "Interest rate discounts"},
    
    # Sanctum - Borrow Delta (IR discounts)
    "INF/SOL": {"team": "Sanctum", "type": "borrow", "description": "Interest rate discounts"},
    
    # PST Team - Borrow Delta (IR discounts)
    "PST/USDC": {"team": "PST Team", "type": "borrow", "description": "Interest rate discounts"},
    
    # Lombard + Fluid - Borrow Delta (IR discounts)
    "LBTC/USDC": {"team": "Lombard + Fluid", "type": "borrow", "description": "Interest rate discounts"},
}

# Lending Token Mapping
LENDING_MAPPING = {
    "USDC": {"team": "Jupiter", "description": "Lending incentives"},
    "USDT": {"team": "Fluid Team", "description": "Lending incentives"},
    "EURC": {"team": "Fluid Team", "description": "Lending incentives"},
    "USDS": {"team": "Fluid Team", "description": "Lending incentives"},
    "USDG": {"team": "Fluid Team", "description": "Lending incentives"},
}

# Token Decimals (from API, but hardcoded as backup)
TOKEN_DECIMALS = {
    "WSOL": 9,
    "SOL": 9,
    "USDC": 6,
    "USDT": 6,
    "EURC": 6,
    "USDS": 6,
    "USDG": 6,
    "cbBTC": 8,
    "xBTC": 8,
    "LBTC": 8,
    "syrupUSDC": 6,
    "JUPSOL": 9,
    "JitoSOL": 9,
    "INF": 9,
    "PST": 9,
}

# Alert Thresholds (USD)
VAULT_SUPPLY_THRESHOLD = 300000  # $300k
VAULT_BORROW_THRESHOLD = 100000  # $100k
LENDING_THRESHOLD = 300000       # $300k

# Google Sheets Configuration
GOOGLE_SHEETS_ENABLED = False
GOOGLE_SHEET_ID = ""  # To be filled during setup
SHEET_NAMES = {
    "vault_rewards": "Vault Rewards",
    "lending_rewards": "Lending Rewards",
    "daily_summary": "Daily Summary",
    "rebalance_log": "Rebalance Log"
}

# GitHub Actions Schedule (Cron format)
# Default: 9 AM IST = 3:30 AM UTC
CRON_SCHEDULE = "30 3 * * *"

# Timezone
TIMEZONE = "Asia/Kolkata"
