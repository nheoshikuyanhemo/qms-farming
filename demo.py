#!/usr/bin/env python3
"""
Quick demo of QMS Testnet farming bot functionality
Run in test mode (no private key required)
"""
from qms_client import QMSClient

def demo():
    print("=" * 60)
    print("QMS TESTNET FARMING BOT - DEMO (TEST MODE)")
    print("=" * 60)
    
    # Initialize in test mode
    client = QMSClient(skip_auth=True)
    
    print("\n--- Balance Checking ---")
    print(f"Chain ID: {client.w3.eth.chain_id}")
    print(f"Router: 0x93AFF45f28e5DF1b55f5AEFEfB807De843b12619")
    
    # Check balances (will be 0 in test mode)
    print("\nWallet Balances:")
    for symbol in ['QMS', 'WQMS', 'USDT', 'USDC', 'WBTC', 'WETH']:
        balance = client.get_balance(symbol)
        human = client.wei_to_human(balance, symbol)
        print(f"  {symbol}: {human}")
    
    # Amount conversion demo
    print("\n--- Amount Conversion Demo ---")
    amount_human = "0.01"
    amount_wei = client.human_to_wei(amount_human, 'WQMS')
    print(f"{amount_human} WQMS = {amount_wei} wei")
    print(f"{amount_wei} wei = {client.wei_to_human(amount_wei, 'WQMS')} WQMS")
    
    # Swap estimation demo
    print("\n--- Swap Estimation Demo ---")
    path = [client.token_contracts['WQMS'].address, client.token_contracts['USDT'].address]
    amount_in = client.human_to_wei("1", 'WQMS')
    try:
        amounts = client.get_swap_output(amount_in, path)
        print(f"1 WQMS -> USDT: {client.wei_to_human(amounts[-1], 'USDT')} USDT")
        print(f"(Amounts out: {[client.wei_to_human(x, 'USDT') for x in amounts]})")
    except Exception as e:
        print(f"Cannot estimate swap: {e}")
    
    # Approval simulation
    print("\n--- Approval Simulation ---")
    print("Approving 100 USDT for router...")
    print("[TEST MODE] Would approve USDT for router: 0x93AFF45f28e5DF1b55f5AEFEfB807De843b12619")
    
    # Swap simulation
    print("\n--- Swap Simulation ---")
    print("Swapping 0.5 WQMS -> USDT...")
    print("[TEST MODE] Would call swapExactTokensForTokens")
    print("  Amount in: 0.5 WQMS")
    print("  Path: WQMS -> USDT")
    print("  Min out: (calculated with 1% slippage)")
    print("  To: [wallet address]")
    print("  Deadline: [now + 20 minutes]")
    
    # Liquidity simulation
    print("\n--- Add Liquidity Simulation ---")
    print("Adding liquidity to WQMS/USDT pool...")
    print("[TEST MODE] Would call addLiquidity")
    print("  Token A: WQMS")
    print("  Token B: USDT")
    print("  Amount A desired: 0.1 WQMS")
    print("  Amount B desired: (calculated from pool ratio)")
    print("  Amount A min: (99% of desired)")
    print("  Amount B min: (99% of desired)")
    print("  To: [wallet address]")
    print("  Deadline: [now + 20 minutes]")
    
    print("\n" + "=" * 60)
    print("To run with real transactions:")
    print("1. Set your private key in .env")
    print("2. Remove skip_auth=True from client initialization")
    print("3. Run: python3 farming_bot.py")
    print("=" * 60)

if __name__ == "__main__":
    demo()