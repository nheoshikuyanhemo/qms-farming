#!/usr/bin/env python3
"""
QMS Testnet Farming Bot
Automatic Wrap/Swap/Add Liquidity/Unwrap/Remove Liquidity with manual input and random/sequential execution
"""
import os
import sys
import time
import random
from dotenv import load_dotenv
from web3 import Web3

load_dotenv('/root/qms-farming/.env')

from qms_client import (
    QMSClient, TOKENS, POOLS,
    get_user_input, get_user_choice, print_balances, get_user_float, get_user_int, pool_to_pairs
)

client = QMSClient()

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')

def ask_run_mode():
    while True:
        mode = get_user_choice("Run mode:", ["Single run (ask each time)", "BATCH mode (set amount/repeats once)", "SEEDED random"])
        if mode in ["Single run (ask each time)", "BATCH mode (set amount/repeats once)", "SEEDED random"]:
            return mode
        time.sleep(1)
        return mode

def ask_order_mode():
    mode = get_user_choice("Order mode:", ["Sequential", "Random"])
    time.sleep(1)
    return mode

def wrap_once(client, amount_str: str):
    """Single wrap operation - raises StopIteration on failure to skip cycle"""
    try:
        amount = float(amount_str)
        if amount <= 0:
            print("Amount must be greater than 0")
            return
        qms_bal = client.get_balance('QMS')
        amount_wei = client.human_to_wei(amount_str, 'QMS')
        if amount_wei > qms_bal:
            print(f"Insufficient QMS balance: have {client.wei_to_human(qms_bal, 'QMS')}, need {amount} QMS")
            raise StopIteration("skip")
        print(f"\nWrapping {amount} QMS -> WQMS...")
        hash = client.wrap_qms(amount_str)
        print(f"WQMS balance after: {client.wei_to_human(client.get_balance('WQMS'), 'WQMS')} WQMS")
    except StopIteration:
        raise
    except Exception as e:
        print(f"Wrap failed: {e}")
        raise StopIteration("skip")
    time.sleep(4)

def unwrap_once(client, amount_str: str):
    """Single unwrap operation - raises StopIteration on failure to skip cycle"""
    try:
        amount = float(amount_str)
        if amount <= 0:
            print("Amount must be greater than 0")
            return
        wqms_bal = client.get_balance('WQMS')
        amount_wei = client.human_to_wei(amount_str, 'WQMS')
        if amount_wei > wqms_bal:
            print(f"Insufficient WQMS balance: have {client.wei_to_human(wqms_bal, 'WQMS')}, need {amount} WQMS")
            raise StopIteration("skip")
        print(f"\nUnwrapping {amount} WQMS -> QMS...")
        hash = client.unwrap_wqms(amount_str)
        print(f"QMS balance after: {client.wei_to_human(client.get_balance('QMS'), 'QMS')} QMS")
    except StopIteration:
        raise
    except Exception as e:
        print(f"Unwrap failed: {e}")
        raise StopIteration("skip")
    time.sleep(4)

def swap_once(client, amount_str: str = None, src: str = None, tgt: str = None):
    """Single swap operation - nonce-safe, waits for receipt before next tx"""
    while amount_str is None:
        amount_str = get_user_float("Enter amount to swap (human readable):")
    
    amount = float(amount_str)
    if amount <= 0:
        print("Amount must be greater than 0")
        return
    
    if src is None:
        src = get_user_choice("From token (e.g., WQMS, USDT, WETH, WBTC, USDC):", list(TOKENS.keys())[:-1])
    
    if tgt is None:
        targets = [t for t in TOKENS.keys() if t != src]
        tgt = get_user_choice("To token (e.g., WQMS, USDT, WETH, WBTC, USDC, QMS):", targets)
    
    print(f"\nSwapping {amount} {src} -> {tgt}")
    print(f"Source balance: {client.wei_to_human(client.get_balance(src), src)} {src}")
    
    amount_in = client.human_to_wei(str(amount), src)
    
    # Unwrap: QMS target (WQMS -> QMS via withdraw)
    if tgt == 'QMS':
        wqms_bal = client.get_balance('WQMS')
        if amount_in > wqms_bal:
            print(f"Insufficient WQMS balance: have {client.wei_to_human(wqms_bal, 'WQMS')}, need {amount} WQMS")
            raise StopIteration("skip")
        try:
            hash = client.unwrap_wqms(amount_str)
            print(f"Success: 0x{hash}")
            print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{hash}")
        except Exception as e:
            print(f"Unwrap failed: {e}")
            raise StopIteration("skip")
        print_balances(client)
        time.sleep(4)
        return
    
    # Native QMS source: wrap + swapETHForTokens
    if src == 'QMS':
        qms_bal = client.get_balance('QMS')
        if amount_in > qms_bal:
            print(f"Insufficient QMS balance: have {client.wei_to_human(qms_bal, 'QMS')}, need {amount} QMS")
            raise StopIteration("skip")
        print("Wrapping QMS -> WQMS first...")
        wqms_hash = client.wrap_qms(amount_str)
        print(f"Wrapped: 0x{wqms_hash}")
        time.sleep(3)
        path = [client.token_contracts['WQMS'].address, client.token_contracts[tgt].address]
        try:
            amounts = client.get_swap_output(amount_in, path)
            print(f"Expected output: {client.wei_to_human(amounts[-1], tgt)} {tgt}")
        except Exception as e:
            print(f"Cannot estimate output: {e}")
            amounts = None
        amount_out_min = int(amount_in * 0.99) if amounts is None else int(amounts[-1] * 0.99)
        try:
            hash = client.swap_exact_wqms_for_tokens(amount_in, amount_out_min, [tgt])
            print(f"Success: 0x{hash}")
            print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{hash}")
        except Exception as e:
            print(f"Swap failed: {e}")
            raise StopIteration("skip")
        print_balances(client)
        time.sleep(3)
        return
    
    # Regular ERC20 -> ERC20 swap
    path = [client.token_contracts[src].address, client.token_contracts[tgt].address]
    
    try:
        amounts = client.get_swap_output(amount_in, path)
        print(f"Expected output: {client.wei_to_human(amounts[-1], tgt)} {tgt}")
    except Exception as e:
        print(f"Cannot estimate output: {e}")
        amounts = None
    
    # Approve exact amount only (non-wqms/native tokens)
    if src != 'WQMS':
        client.ensure_allowance(src, client.router.address, amount_in)
    
    # Minimum out (with slippage)
    if amounts:
        amount_out_min = int(amounts[-1] * 0.99)
    else:
        amount_out_min = 0
    
    print("\nExecuting swap...")
    try:
        hash = client.swap_exact_tokens_for_tokens(amount_in, amount_out_min, path)
        print(f"Success: 0x{hash}")
        print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{hash}")
    except Exception as e:
        print(f"Swap failed: {e}")
        raise StopIteration("skip")
    print_balances(client)
    time.sleep(3)

def add_liquidity_once(client, pool: str = None, token_a: str = None, amount_a_str: str = None):
    """Single add liquidity operation - user specifies token A amount, token B auto-calculated from pool price"""
    while pool is None:
        pool = get_user_choice("Select pool:", list(POOLS.keys()))
    
    pair = pool_to_pairs(pool)
    if token_a is None:
        token_a = get_user_choice("Select token A (user-defined amount):", pair)
    # Determine token B as the other token in the pair
    token_b = [t for t in pair if t != token_a][0]
    print(f"Token B will be {token_b} (amount auto-calculated from pool price)")
    
    amount_a_str = amount_a_str or get_user_float(f"Enter amount for {token_a} (human readable):")
    
    amount_a = float(amount_a_str)
    if amount_a <= 0:
        print("Amount must be greater than 0")
        return
    
    print(f"\nAdding liquidity to {token_a}/{token_b} pool ({pool})")
    print(f"User amount: {amount_a} {token_a}")
    print(f"Balance {token_a}: {client.wei_to_human(client.get_balance(token_a), token_a)} {token_a}")
    print(f"Balance {token_b}: {client.wei_to_human(client.get_balance(token_b), token_b)} {token_b}")
    
    amount_a_wei = client.human_to_wei(str(amount_a), token_a)
    
    # Check balance
    bal_a = client.get_balance(token_a)
    if amount_a_wei > bal_a:
        print(f"Insufficient {token_a} balance: have {client.wei_to_human(bal_a, token_a)}, need {amount_a} {token_a}")
        raise StopIteration("skip")
    
    # Auto-calculate token B amount based on pool price (reserves ratio)
    pool_name = None
    for name, addr in POOLS.items():
        pair_check = pool_to_pairs(name)
        if set(pair_check) == set([token_a, token_b]):
            pool_name = name
            break
    
    if not pool_name:
        print(f"No pool found for {token_a}/{token_b}")
        raise StopIteration("skip")
    
    pool_contract = client.pool_contracts[pool_name]
    reserves = pool_contract.functions.getReserves().call()
    reserve_a = int(reserves[0])
    reserve_b = int(reserves[1])
    
    # Calculate token B amount based on pool price ratio
    # amount_b = amount_a * (reserve_b / reserve_a)
    amount_b_wei = (amount_a_wei * reserve_b) // reserve_a
    amount_b_human = client.wei_to_human(amount_b_wei, token_b)
    
    print(f"\nCalculated token B amount (based on pool price): {amount_b_human} {token_b}")
    print(f"Pool reserves ratio: {client.wei_to_human(reserve_a, token_a)} {token_a} / {client.wei_to_human(reserve_b, token_b)} {token_b}")
    
    # Check balance of token B
    bal_b = client.get_balance(token_b)
    if amount_b_wei > bal_b:
        print(f"Insufficient {token_b} balance: have {client.wei_to_human(bal_b, token_b)}, need {amount_b_human} {token_b}")
        raise StopIteration("skip")
    
    # Approve both tokens for the router
    client.ensure_allowance(token_a, client.router.address, amount_a_wei)
    client.ensure_allowance(token_b, client.router.address, amount_b_wei)
    
    # Add liquidity with auto-calculated amount B
    amount_a_min = int(amount_a_wei * 0.98)
    amount_b_min = int(amount_b_wei * 0.98)
    
    print(f"\nAdding liquidity to {pool_name} with {client.wei_to_human(amount_a_wei, token_a)} {token_a} and {client.wei_to_human(amount_b_wei, token_b)} {token_b}")
    try:
        hash = client.add_liquidity(token_a, token_b, amount_a_wei, amount_b_wei, amount_a_min, amount_b_min)
        print(f"Success: 0x{hash}")
        print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{hash}")
    except Exception as e:
        print(f"Add liquidity failed: {e}")
        raise StopIteration("skip")
    print_balances(client)
    time.sleep(4)

def _add_liquidity_with_tokens(client, token_a: str, token_b: str, amount_a: float = None, amount_b: float = None):
    """Add liquidity with two tokens (separate amounts) - nonce-safe"""
    while amount_a is None:
        amount_a = get_user_float(f"Enter amount for {token_a} (human readable):")
    while amount_b is None:
        amount_b = get_user_float(f"Enter amount for {token_b} (human readable):")
    
    amount_a = float(amount_a)
    amount_b = float(amount_b)
    if amount_a <= 0 or amount_b <= 0:
        print("Amounts must be greater than 0")
        return
    
    amount_a_wei = client.human_to_wei(str(amount_a), token_a)
    amount_a_min = int(amount_a_wei * 0.98)
    amount_b_min = None  # Will be auto-calculated in add_liquidity
    
    bal_a = client.get_balance(token_a)
    if amount_a_wei > bal_a:
        print(f"Insufficient {token_a} balance: have {client.wei_to_human(bal_a, token_a)}, need {amount_a} {token_a}")
        raise StopIteration("skip")
    
    client.ensure_allowance(token_a, client.router.address, amount_a_wei)
    
    pool_name = None
    for name, addr in POOLS.items():
        pair = pool_to_pairs(name)
        if set(pair) == set([token_a, token_b]):
            pool_name = name
            break
    
    if not pool_name:
        print(f"No pool found for {token_a}/{token_b}")
        raise StopIteration("skip")
    
    print(f"\nAdding liquidity to {pool_name}...")
    try:
        hash = client.add_liquidity(token_a, token_b, amount_a_wei, None, amount_a_min, None)
    except Exception as e:
        print(f"Add liquidity failed: {e}")
        raise StopIteration("skip")
    print_balances(client)
    time.sleep(4)

def remove_liquidity_once(client, pool: str = None, amount_a_str: str = None):
    """Single remove liquidity operation - user specifies token A amount, token B auto-calculated from pool price"""
    while pool is None:
        pool = get_user_choice("Select pool to remove from:", list(POOLS.keys()))
    
    pair = pool_to_pairs(pool)
    if amount_a_str is None:
        amount_a_str = get_user_float(f"Enter amount for {pair[0]} (human readable):")
    
    amount_a = float(amount_a_str)
    if amount_a <= 0:
        print("Amount must be greater than 0")
        return
    
    token_a = pair[0]
    token_b = pair[1]
    
    print(f"\nRemoving liquidity from {token_a}/{token_b} pool ({pool})")
    print(f"User amount: {amount_a} {token_a}")
    print(f"Balance {token_a}: {client.wei_to_human(client.get_balance(token_a), token_a)} {token_a}")
    print(f"Balance {token_b}: {client.wei_to_human(client.get_balance(token_b), token_b)} {token_b}")
    
    amount_a_wei = client.human_to_wei(str(amount_a), token_a)
    
    # Check balance
    bal_a = client.get_balance(token_a)
    if amount_a_wei > bal_a:
        print(f"Insufficient {token_a} balance: have {client.wei_to_human(bal_a, token_a)}, need {amount_a} {token_a}")
        raise StopIteration("skip")
    
    # Auto-calculate token B amount based on pool price (reserves ratio)
    pool_name = None
    for name, addr in POOLS.items():
        pair_check = pool_to_pairs(name)
        if set(pair_check) == set([token_a, token_b]):
            pool_name = name
            break
    
    if not pool_name:
        print(f"No pool found for {token_a}/{token_b}")
        raise StopIteration("skip")
    
    pool_contract = client.pool_contracts[pool_name]
    reserves = pool_contract.functions.getReserves().call()
    reserve_a = int(reserves[0])
    reserve_b = int(reserves[1])
    
    # Calculate token B amount based on pool price ratio
    # amount_b = amount_a * (reserve_b / reserve_a)
    amount_b_wei = (amount_a_wei * reserve_b) // reserve_a
    amount_b_human = client.wei_to_human(amount_b_wei, token_b)
    
    print(f"\nCalculated token B amount (based on pool price): {amount_b_human} {token_b}")
    print(f"Pool reserves ratio: {client.wei_to_human(reserve_a, token_a)} {token_a} / {client.wei_to_human(reserve_b, token_b)} {token_b}")
    
    # Check balance of token B
    bal_b = client.get_balance(token_b)
    if amount_b_wei > bal_b:
        print(f"Insufficient {token_b} balance: have {client.wei_to_human(bal_b, token_b)}, need {amount_b_human} {token_b}")
        raise StopIteration("skip")
    
    # Approve both tokens for the router
    client.ensure_allowance(token_a, client.router.address, amount_a_wei)
    client.ensure_allowance(token_b, client.router.address, amount_b_wei)
    
    # Add liquidity with auto-calculated amount B
    amount_a_min = int(amount_a_wei * 0.98)
    amount_b_min = int(amount_b_wei * 0.98)
    
    print(f"\nRemoving liquidity from {pool_name} with {client.wei_to_human(amount_a_wei, token_a)} {token_a} and {client.wei_to_human(amount_b_wei, token_b)} {token_b}")
    try:
        hash = client.remove_liquidity(token_a, token_b, amount_a_wei, amount_a_min, amount_b_min)
        print(f"Success: 0x{hash}")
        print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{hash}")
    except Exception as e:
        print(f"Remove liquidity failed: {e}")
        raise StopIteration("skip")
    print_balances(client)
    time.sleep(4)

def run_all_flow(client):
    """Run all operations: Wrap -> Swap Random -> Add Liquidity Random -> Unwrap -> Remove Liquidity"""
    clear()
    print("=" * 60)
    print("   QMS TESTNET FARMING BOT")
    print("   Network: QMS Testnet | Chain ID: 19480")
    print("=" * 60)
    print("1. WRAP QMS -> WQMS")
    print("2. SWAP tokens")
    print("3. ADD LIQUIDITY")
    print("4. UNWRAP WQMS -> QMS")
    print("5. REMOVE LIQUIDITY")
    print("6. Check Balances")
    print("7. Exit")
    print("-" * 60)
    
    print_balances(client)
    print()
    
    print("=" * 60)
    print("   CONFIGURE RUN ALL - Per Token Amounts")
    print("=" * 60)
    
    # Wrap amount
    wrap_amount = get_user_float("Enter amount of QMS to wrap (human readable):", "0.1")
    
    # Swap amounts - per token
    print("\n--- SWAP Amounts (per token) ---")
    swap_amounts = {}
    all_tokens = list(TOKENS.keys())[:-1]  # exclude QMS native
    for token in all_tokens:
        bal = client.wei_to_human(client.get_balance(token), token)
        amt = get_user_float(f"  {token} (balance: {bal}):", "0.01")
        swap_amounts[token] = amt
    
    # Add liquidity amounts - per token (token A only, token B auto-calculated from pool price)
    print("\n--- ADD LIQUIDITY Amounts (token A only, token B auto from pool price) ---")
    liq_amounts = {}
    for token in all_tokens:
        bal = client.wei_to_human(client.get_balance(token), token)
        amt = get_user_float(f"  {token} as token A (balance: {bal}):", "0.01")
        liq_amounts[token] = amt
    
    # Remove liquidity amounts - per token (token A only, token B auto-calculated from pool price)
    print("\n--- REMOVE LIQUIDITY Amounts (token A only, token B auto from pool price) ---")
    remove_amounts = {}
    for token in all_tokens:
        bal = client.wei_to_human(client.get_balance(token), token)
        amt = get_user_float(f"  {token} as token A (balance: {bal}):", "0.05")
        remove_amounts[token] = amt
    
    repeats = get_user_int("Enter number of repetitions (how many cycles):", 1)
    
    all_pools = list(POOLS.keys())
    
    for cycle in range(1, repeats + 1):
        print(f"\n{'='*60}")
        print(f"   CYCLE {cycle}/{repeats}")
        print(f"{'='*60}")
        
        # Step 1: Wrap QMS -> WQMS
        print("\n" + "=" * 60)
        print("STEP 1: WRAP QMS -> WQMS")
        print("=" * 60)
        print(f"QMS balance: {client.wei_to_human(client.get_balance('QMS'), 'QMS')} QMS")
        print(f"WQMS balance: {client.wei_to_human(client.get_balance('WQMS'), 'WQMS')} WQMS")
        
        try:
            wrap_once(client, str(wrap_amount))
            print(f"\nWrapped {wrap_amount} QMS -> {client.wei_to_human(client.get_balance('WQMS'), 'WQMS')} WQMS")
        except StopIteration:
            print(f"Skipping cycle {cycle} due to insufficient balance")
            continue
        time.sleep(3)
        
        # Step 2: Swap - Random token pairs with per-token amounts
        print("\n" + "=" * 60)
        print("STEP 2: SWAP TOKENS (Random Pairs)")
        print("=" * 60)
        print_balances(client)
        print()
        
        random.shuffle(all_tokens)
        src = all_tokens[0]
        targets = [t for t in all_tokens if t != src]
        random.shuffle(targets)
        tgt = targets[0]
        
        # Use per-token amount for the source token
        swap_amt = swap_amounts.get(src, 0.01)
        print(f"Random pair: {src} -> {tgt} (using {swap_amt} {src})")
        try:
            swap_once(client, str(swap_amt), src, tgt)
            print(f"Swapped {swap_amt} {src} -> {tgt}")
        except StopIteration:
            print(f"Skipping swap in cycle {cycle} due to insufficient balance/error")
        time.sleep(3)
        
        # Step 3: Add Liquidity - Random pool with per-token amounts
        print("\n" + "=" * 60)
        print("STEP 3: ADD LIQUIDITY (Random Pool)")
        print("=" * 60)
        print_balances(client)
        print()
        
        random.shuffle(all_pools)
        pool = all_pools[0]
        tokens = pool_to_pairs(pool)
        token_a, token_b = tokens
        
        # Use per-token amount for token A in the pool (token B auto-calculated from pool price)
        liq_amt_a = liq_amounts.get(token_a, 0.01)
        
        print(f"Random pool: {pool} ({token_a}/{token_b})")
        print(f"Using {liq_amt_a} {token_a} (token B will be auto-calculated from pool price)")
        try:
            add_liquidity_once(client, pool, token_a, str(liq_amt_a))
            print(f"Added liquidity to {pool}")
        except StopIteration:
            print(f"Skipping liquidity in cycle {cycle} due to insufficient balance/error")
        time.sleep(3)
        
        # Step 4: Unwrap WQMS -> QMS
        print("\n" + "=" * 60)
        print("STEP 4: UNWRAP WQMS -> QMS")
        print("=" * 60)
        wqms_bal = client.get_balance('WQMS')
        print(f"WQMS balance: {client.wei_to_human(wqms_bal, 'WQMS')} WQMS")
        
        try:
            unwrap_once(client, str(client.wei_to_human(wqms_bal, 'WQMS')))
            print(f"Unwrapped {client.wei_to_human(wqms_bal, 'WQMS')} WQMS -> QMS")
        except StopIteration:
            print(f"Skipping unwrap in cycle {cycle} due to insufficient balance")
        time.sleep(3)
        
        # Step 5: Remove Liquidity with per-token amounts
        print("\n" + "=" * 60)
        print("STEP 5: REMOVE LIQUIDITY")
        print("=" * 60)
        
        random.shuffle(all_pools)
        pool_to_remove = all_pools[0]
        pair = pool_to_pairs(pool_to_remove)
        token_a, token_b = pair
        
        remove_amt = remove_amounts.get(token_a, 0.05)
        
        try:
            remove_liquidity_once(client, pool_to_remove, str(remove_amt))
            print(f"Removed liquidity from {pool_to_remove}")
        except StopIteration:
            print(f"Skipping remove in cycle {cycle} due to insufficient balance")
        time.sleep(3)
    
    print("\n" + "=" * 60)
    print("RUN ALL COMPLETED!")
    print("=" * 60)

def main_menu():
    while True:
        clear()
        print("=" * 60)
        print("   QMS TESTNET FARMING BOT")
        print("   Network: QMS Testnet | Chain ID: 19480")
        print("=" * 60)
        print("1. WRAP QMS -> WQMS")
        print("2. SWAP tokens")
        print("3. ADD LIQUIDITY")
        print("4. UNWRAP WQMS -> QMS")
        print("5. REMOVE LIQUIDITY")
        print("6. RUN ALL (Wrap -> Swap -> Add -> Unwrap -> Remove)")
        print("7. Check Balances")
        print("8. Exit")
        print("-" * 60)
        
        choice = get_user_choice("Select option", ["Wrap QMS", "Swap", "Add Liquidity", "Unwrap", "Remove Liquidity", "RUN ALL", "Check Balances", "Exit"])
        
        if choice == "Exit":
            print("Goodbye!")
            sys.exit(0)
        elif choice == "Check Balances":
            print_balances(client)
            time.sleep(3)
        elif choice == "RUN ALL":
            run_all_flow(client)
            time.sleep(3)
        else:
            clear()
            print("=" * 60)
            print("   QMS TESTNET FARMING BOT")
            print("=" * 60)
            print("1. WRAP QMS -> WQMS")
            print("2. SWAP tokens")
            print("3. ADD LIQUIDITY")
            print("4. UNWRAP WQMS -> QMS")
            print("5. REMOVE LIQUIDITY")
            print("-" * 60)
            
            sub = get_user_choice("Operation:", ["Wrap", "Swap", "Add Liquidity", "Unwrap", "Remove Liquidity"])
            
            if sub == "Wrap":
                wrap_flow(client)
            elif sub == "Swap":
                swap_flow(client)
            elif sub == "Add Liquidity":
                add_liquidity_flow(client)
            elif sub == "Unwrap":
                unwrap_flow(client)
            elif sub == "Remove Liquidity":
                remove_liquidity_flow(client)
            
            time.sleep(3)

def wrap_flow(client):
    while True:
        clear()
        print("=" * 60)
        print("   WRAP QMS -> WQMS")
        print("=" * 60)
        print(f"Your balance: {client.wei_to_human(client.get_balance('QMS'), 'QMS')} QMS")
        print(f"WQMS balance: {client.wei_to_human(client.get_balance('WQMS'), 'WQMS')} WQMS")
        print()
        
        mode = ask_run_mode()
        if mode == "Single run (ask each time)":
            amount = get_user_float("Enter amount of QMS to wrap (human readable, e.g., 0.01, 0.1, 1, 11):")
            wrap_once(client, amount)
            more = get_user_choice("Wrap more?", ["Yes", "No"]).lower().startswith('y')
            if more:
                continue
            else:
                return
        else:
            base_amount = get_user_float("Enter base amount of QMS to wrap:")
            repeats = get_user_int("Enter number of repetitions:")
            order = ask_order_mode()
            for i in range(repeats):
                amount = base_amount if order == "Sequential" else base_amount * (1 + random.uniform(-0.05, 0.05))
                wrap_once(client, f"{amount:.6f}" if order == "Random" else str(base_amount))
                print(f"\n[{i+1}/{repeats}] Wrapped {amount:.6f} QMS")
                time.sleep(3)
            return

def unwrap_flow(client):
    while True:
        clear()
        print("=" * 60)
        print("   UNWRAP WQMS -> QMS")
        print("=" * 60)
        print(f"WQMS balance: {client.wei_to_human(client.get_balance('WQMS'), 'WQMS')} WQMS")
        print(f"QMS balance: {client.wei_to_human(client.get_balance('QMS'), 'QMS')} QMS")
        print()
        
        mode = ask_run_mode()
        if mode == "Single run (ask each time)":
            amount = get_user_float("Enter amount of WQMS to unwrap (human readable):")
            unwrap_once(client, amount)
            more = get_user_choice("Unwrap more?", ["Yes", "No"]).lower().startswith('y')
            if more:
                continue
            else:
                return
        else:
            base_amount = get_user_float("Enter base amount of WQMS to unwrap:")
            repeats = get_user_int("Enter number of repetitions:")
            order = ask_order_mode()
            for i in range(repeats):
                amount = base_amount if order == "Sequential" else base_amount * (1 + random.uniform(-0.05, 0.05))
                unwrap_once(client, f"{amount:.6f}" if order == "Random" else str(base_amount))
                print(f"\n[{i+1}/{repeats}] Unwrapped {amount:.6f} WQMS")
                time.sleep(3)
            return

def swap_flow(client):
    while True:
        clear()
        print("=" * 60)
        print("   SWAP TOKENS")
        print("=" * 60)
        print_balances(client)
        print()
        print("Available tokens:", ", ".join(TOKENS.keys()))
        print()
        
        mode = ask_run_mode()
        
        if mode == "Single run (ask each time)":
            swap_once(client)
            more = get_user_choice("Swap more?", ["Yes", "No"]).lower().startswith('y')
            if more:
                continue
            else:
                return
        else:
            base_amount = get_user_float("Enter base amount to swap (human readable, e.g., 0.01, 0.1, 1, 11):")
            repeats = get_user_int("Enter number of repetitions:")
            order = ask_order_mode()
            for i in range(repeats):
                amount = base_amount if order == "Sequential" else base_amount * (1 + random.uniform(-0.05, 0.05))
                swap_once(client, f"{amount:.6f}" if order == "Random" else str(base_amount))
                print(f"\n[{i+1}/{repeats}] Swapped {amount:.6f}")
                time.sleep(3)
            return

def add_liquidity_flow(client):
    while True:
        clear()
        print("=" * 60)
        print("   ADD LIQUIDITY")
        print("=" * 60)
        print_balances(client)
        print()
        print("Available pools:", ", ".join(POOLS.keys()))
        print()
        
        mode = ask_run_mode()
        
        if mode == "Single run (ask each time)":
            add_liquidity_once(client)
            more = get_user_choice("Add more liquidity?", ["Yes", "No"]).lower().startswith('y')
            if more:
                continue
            else:
                return
        else:
            pool = get_user_choice("Select pool:", list(POOLS.keys()))
            # For batch mode, ask for token A amounts for each token in the pool
            pair = pool_to_pairs(pool)
            print(f"Pool tokens: {pair[0]} / {pair[1]}")
            token_a = get_user_choice("Select token A (user-defined amount):", pair)
            base_amount = get_user_float(f"Enter base amount for {token_a} (human readable):")
            repeats = get_user_int("Enter number of repetitions:")
            order = ask_order_mode()
            for i in range(repeats):
                amount = base_amount if order == "Sequential" else base_amount * (1 + random.uniform(-0.05, 0.05))
                add_liquidity_once(client, pool, token_a, f"{amount:.6f}" if order == "Random" else str(base_amount))
                print(f"\n[{i+1}/{repeats}] Added liquidity to {pool} with {amount} {token_a}")
                time.sleep(3)
            return

def remove_liquidity_flow(client):
    while True:
        clear()
        print("=" * 60)
        print("   REMOVE LIQUIDITY")
        print("=" * 60)
        print_balances(client)
        print()
        print("Available pools:", ", ".join(POOLS.keys()))
        print()
        
        mode = ask_run_mode()
        
        if mode == "Single run (ask each time)":
            remove_liquidity_once(client)
            more = get_user_choice("Remove more liquidity?", ["Yes", "No"]).lower().startswith('y')
            if more:
                continue
            else:
                return
        else:
            pool = get_user_choice("Select pool to remove from:", list(POOLS.keys()))
            base_amount = get_user_float("Enter base amount to remove (human readable):")
            repeats = get_user_int("Enter number of repetitions:")
            order = ask_order_mode()
            for i in range(repeats):
                amount = base_amount if order == "Sequential" else base_amount * (1 + random.uniform(-0.05, 0.05))
                remove_liquidity_once(client, pool, f"{amount:.6f}" if order == "Random" else str(base_amount))
                print(f"\n[{i+1}/{repeats}] Removed liquidity from {pool}")
                time.sleep(3)
            return

if __name__ == "__main__":
    main_menu()
