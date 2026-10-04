"""
QMS Testnet Core Utility Module (QWAP.xyz router)
Handles Web3 connection, contract interactions, and common utilities
"""
import os
import json
import time
import random
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv

# Load environment
load_dotenv('/root/qms-farming/.env')

# Network Configuration
CHAIN_ID = int(os.getenv('CHAIN_ID', '19480'))
RPC_URL = os.getenv('RPC_URL', 'https://rpc.testnet.qms.finance')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
ROUTER_ADDRESS = Web3.to_checksum_address(os.getenv('ROUTER_ADDRESS'))

# Token Addresses
TOKENS = {
    'USDT': Web3.to_checksum_address(os.getenv('USDT')),
    'USDC': Web3.to_checksum_address(os.getenv('USDC')),
    'WBTC': Web3.to_checksum_address(os.getenv('WBTC')),
    'WQMS': Web3.to_checksum_address(os.getenv('WQMS')),
    'WETH': Web3.to_checksum_address(os.getenv('WETH')),
    'QMS': '0x0000000000000000000000000000000000000000',  # Native QMS
}

# Pool Addresses
POOLS = {
    'USDT_WBTC': Web3.to_checksum_address(os.getenv('POOL_USDT_WBTC')),
    'WQMS_WBTC': Web3.to_checksum_address(os.getenv('POOL_WQMS_WBTC')),
    'WQMS_WETH': Web3.to_checksum_address(os.getenv('POOL_WQMS_WETH')),
    'WETH_USDC': Web3.to_checksum_address(os.getenv('POOL_WETH_USDC')),
    'WQMS_USDC': Web3.to_checksum_address(os.getenv('POOL_WQMS_USDC')),
    'USDT_WQMS': Web3.to_checksum_address(os.getenv('POOL_USDT_WQMS')),
}

# Pool ABI (minimal - just getReserves, token0, token1)
POOL_ABI = json.loads('''[
    {"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}
]''')

def pool_to_pairs(pool_name: str) -> List[str]:
    """Get token pair for a pool name"""
    pairs = {
        'USDT_WBTC': ['USDT', 'WBTC'],
        'WQMS_WBTC': ['WQMS', 'WBTC'],
        'WQMS_WETH': ['WQMS', 'WETH'],
        'WETH_USDC': ['WETH', 'USDC'],
        'WQMS_USDC': ['WQMS', 'USDC'],
        'USDT_WQMS': ['USDT', 'WQMS'],
    }
    return pairs.get(pool_name, [])

# ERC20 ABI (minimal)
ERC20_ABI = json.loads('''[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"}
]''')

# WQMS ABI (WETH-style)
WQMS_ABI = json.loads('''[
    {"constant":false,"inputs":[],"name":"deposit","outputs":[],"type":"function","payable":true},
    {"constant":false,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"type":"function"},
    {"constant":true,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}
]''')

# Router ABI (Uniswap V2 style)
ROUTER_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactETH","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactTokens","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"WQMS","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}
]''')


class QMSClient:
    def __init__(self, skip_auth=False):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to {RPC_URL}")
        
        # Verify chain ID
        actual_chain_id = self.w3.eth.chain_id
        if actual_chain_id != CHAIN_ID:
            print(f"Warning: Chain ID mismatch. Expected {CHAIN_ID}, got {actual_chain_id}")
        
        # Account setup
        if not PRIVATE_KEY or PRIVATE_KEY == '0x0000000000000000000000000000000000000000000000000000000000000000':
            if skip_auth:
                print("Warning: No PRIVATE_KEY provided - running in test mode (no transactions)")
                self.account = None
                self.address = None
            else:
                raise ValueError("PRIVATE_KEY not set in .env")
        else:
            self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
            self.address = self.account.address
        
        # Contract instances
        self.router = self.w3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)
        self.wqms = self.w3.eth.contract(address=TOKENS['WQMS'], abi=WQMS_ABI)
        
        # Token contracts
        self.token_contracts = {}
        for symbol, addr in TOKENS.items():
            if addr != '0x0000000000000000000000000000000000000000':
                self.token_contracts[symbol] = self.w3.eth.contract(address=addr, abi=ERC20_ABI)
        
        # Pool contracts
        self.pool_contracts = {}
        for name, addr in POOLS.items():
            self.pool_contracts[name] = self.w3.eth.contract(address=addr, abi=POOL_ABI)
        
        print(f"Connected to QMS Testnet (Chain ID: {self.w3.eth.chain_id})")
        if self.account:
            print(f"Wallet: {self.address}")
        else:
            print("Wallet: None (test mode)")
        print(f"Router: {ROUTER_ADDRESS}")
    
    def get_nonce(self):
        if not self.account:
            return 0
        return self.w3.eth.get_transaction_count(self.address)
    
    def get_gas_price(self):
        """Get gas price with 20% buffer to avoid 'replacement transaction underpriced' errors"""
        base = self.w3.eth.gas_price
        return int(base * 1.2)
    
    def _prepare_tx(self, tx_dict: dict) -> dict:
        """Prepare a tx dict for signing: fresh nonce, legacy gasPrice, gas estimate,
        and strip any EIP-1559 fee fields that build_transaction may have auto-filled.
        This guarantees every tx (approval, swap, addLiquidity, wrap) signs consistently."""
        if not self.account:
            return tx_dict
        tx_dict.setdefault('chainId', CHAIN_ID)
        tx_dict.setdefault('from', self.address)
        tx_dict['nonce'] = self.get_nonce()
        tx_dict.setdefault('gasPrice', self.get_gas_price())
        if 'gas' not in tx_dict:
            try:
                tx_dict['gas'] = self.w3.eth.estimate_gas(tx_dict)
            except Exception:
                tx_dict['gas'] = 500000
        # Force legacy tx: drop EIP-1559 fee fields
        for key in ('maxFeePerGas', 'maxPriorityFeePerGas', 'type'):
            tx_dict.pop(key, None)
        return tx_dict
    
    def get_balance(self, token_symbol: str) -> int:
        """Get token balance in wei"""
        if not self.account:
            return 0
        if token_symbol == 'QMS':
            return self.w3.eth.get_balance(self.address)
        if token_symbol in self.token_contracts:
            return self.token_contracts[token_symbol].functions.balanceOf(self.address).call()
        raise ValueError(f"Unknown token: {token_symbol}")
    
    def get_decimals(self, token_symbol: str) -> int:
        """Get token decimals"""
        token_symbol = self._token_symbol_from(token_symbol)
        if token_symbol == 'QMS':
            return 18
        if token_symbol in self.token_contracts:
            return self.token_contracts[token_symbol].functions.decimals().call()
        raise ValueError(f"Unknown token: {token_symbol}")
    
    def human_to_wei(self, amount: str, token_symbol: str) -> int:
        """Convert human-readable amount to wei (e.g., '0.01' -> 10000000000000000)"""
        decimals = self.get_decimals(token_symbol)
        return int(Decimal(amount) * (10 ** decimals))
    
    def wei_to_human(self, amount_wei: int, token_symbol: str) -> str:
        """Convert wei to human-readable string"""
        decimals = self.get_decimals(token_symbol)
        return str(Decimal(amount_wei) / (10 ** decimals))
    
    def _token_symbol_from(self, token: str) -> str:
        """Resolve token symbol from either symbol or address"""
        if token in TOKENS:
            return token
        # Try to find symbol by address
        for sym, addr in TOKENS.items():
            if Web3.to_checksum_address(addr) == Web3.to_checksum_address(token):
                return sym
        return token
    
    def check_allowance(self, token_symbol: str, spender: str) -> int:
        """Check token allowance for spender"""
        if not self.account:
            return 2**256 - 1
        token_symbol = self._token_symbol_from(token_symbol)
        if token_symbol == 'QMS':
            return 2**256 - 1  # Native token doesn't need approval
        token = self.token_contracts[token_symbol]
        return token.functions.allowance(self.address, spender).call()
    
    def approve_token(self, token_symbol: str, spender: str, amount: int = None) -> str:
        """Approve token for spender. Waits for tx to be mined."""
        if not self.account:
            print(f"[TEST MODE] Would approve {token_symbol} for {spender}")
            return "0x0000000000000000000000000000000000000000000000000000000000000000"
        
        if token_symbol == 'QMS':
            return None  # Native token doesn't need approval
        
        token = self.token_contracts[token_symbol]
        if amount is None:
            amount = 2**256 - 1  # Max approval
        
        # Build approve transaction
        approve_tx = token.functions.approve(spender, amount).build_transaction({
            'from': self.address,
            'nonce': self.get_nonce(),
            'gasPrice': self.get_gas_price(),
            'gas': 100000,
            'chainId': CHAIN_ID,
        })
        
        # Sign and send
        signed = self.w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        # Wait for mining receipt
        print(f"Waiting for {token_symbol} approval to be mined...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            token_symbol = self._token_symbol_from(token_symbol)
            print(f"Approved {token_symbol} for {spender}: 0x{tx_hash.hex()}")
        else:
            print(f"Approval failed: 0x{tx_hash.hex()}")
            raise RuntimeError(f"Approval transaction failed: {tx_hash.hex()}")
        
        return tx_hash.hex()
    
    def ensure_allowance(self, token_symbol: str, spender: str, required_amount: int) -> bool:
        """Ensure sufficient allowance, approve if needed.
        Approves required_amount + 1% buffer to cover gas fees/rounding so
        the actual transfer never fails due to balance being 1 wei short."""
        if not self.account:
            print(f"[TEST MODE] Ensuring allowance for {token_symbol}")
            return True
        if token_symbol == 'QMS':
            return True
        
        current = self.check_allowance(token_symbol, spender)
        # Add 1% buffer on top of required amount for approval
        approved_amount = required_amount * 101 // 100
        if current >= approved_amount:
            print(f"Allowance sufficient: {self.wei_to_human(current, token_symbol)} {token_symbol}")
            return True
        
        print(f"Approving {token_symbol} (needed: {self.wei_to_human(required_amount, token_symbol)}, approved: {self.wei_to_human(approved_amount, token_symbol)} incl. 1% buffer)")
        self.approve_token(token_symbol, spender, approved_amount)
        time.sleep(2)  # Wait for approval to be mined
        return True
    
    def send_transaction(self, tx_dict: dict) -> str:
        """Sign and send transaction, return tx hash. Raises exception on failure."""
        if not self.account:
            print("[TEST MODE] Would send transaction:", tx_dict)
            return "0x0000000000000000000000000000000000000000000000000000000000000000"
        
        # Use _prepare_tx to normalize the tx dict (strip EIP-1559 fields, set nonce/gas)
        tx_dict = self._prepare_tx(tx_dict)
        
        # Sign and send
        signed = self.w3.eth.account.sign_transaction(tx_dict, PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"Success: 0x{tx_hash.hex()}")
        else:
            print(f"Failed: 0x{tx_hash.hex()}")
            # Print explorer link for failed tx too
            print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{tx_hash.hex()}")
            raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
        
        # Print explorer link
        if self.account:
            print(f"Explorer: {os.getenv('BLOCK_EXPLORER', 'https://testnet.qmsscan.io')}/tx/0x{tx_hash.hex()}")
        
        return tx_hash.hex()
    
    def wrap_qms(self, amount_qms: str) -> str:
        """Wrap native QMS to WQMS"""
        amount_wei = self.human_to_wei(amount_qms, 'QMS')
        
        tx = self.wqms.functions.deposit().build_transaction({
            'from': self.address,
            'value': amount_wei,
            'nonce': self.get_nonce(),
            'gasPrice': self.get_gas_price(),
            'gas': 100000,
            'chainId': CHAIN_ID,
        })
        
        return self.send_transaction(tx)
    
    def unwrap_wqms(self, amount_wqms: str) -> str:
        """Unwrap WQMS to native QMS"""
        amount_wei = self.human_to_wei(amount_wqms, 'WQMS')
        
        tx = self.wqms.functions.withdraw(amount_wei).build_transaction({
            'from': self.address,
            'nonce': self.get_nonce(),
            'gasPrice': self.get_gas_price(),
            'gas': 100000,
            'chainId': CHAIN_ID,
        })
        
        return self.send_transaction(tx)
    
    def get_swap_output(self, amount_in: int, path: List[str]) -> List[int]:
        """Get expected output amounts for a swap path"""
        checksum_path = [Web3.to_checksum_address(addr) for addr in path]
        return self.router.functions.getAmountsOut(amount_in, checksum_path).call()
    
    def swap_exact_tokens_for_tokens(self, amount_in: int, amount_out_min: int, path: List[str], deadline: int = None) -> str:
        """Swap exact input tokens for output tokens"""
        if deadline is None:
            deadline = int(time.time()) + 1200  # 20 minutes
        
        # Approve the exact amount of input token (not native QMS)
        self.ensure_allowance(path[0], self.router.address, amount_in)
        
        checksum_path = [Web3.to_checksum_address(addr) for addr in path]
        
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            checksum_path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
        })
        
        return self.send_transaction(tx)
    
    def swap_exact_eth_for_tokens(self, amount_out_min: int, path: List[str], value: int, deadline: int = None) -> str:
        """Swap exact ETH (QMS) for tokens"""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # QMS swap doesn't need ERC20 approval, but wrap first if needed
        checksum_path = [Web3.to_checksum_address(addr) for addr in path]
        
        tx = self.router.functions.swapExactETHForTokens(
            amount_out_min,
            checksum_path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
            'value': value,
        })
        
        return self.send_transaction(tx)
    
    def swap_exact_tokens_for_eth(self, amount_in: int, amount_out_min: int, path: List[str], deadline: int = None) -> str:
        """Swap exact tokens for ETH (QMS)"""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # Approve the exact amount of input token (first token in path)
        self.ensure_allowance(path[0], self.router.address, amount_in)
        
        checksum_path = [Web3.to_checksum_address(addr) for addr in path]
        
        tx = self.router.functions.swapExactTokensForETH(
            amount_in,
            amount_out_min,
            checksum_path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
        })
        
        return self.send_transaction(tx)
    
    def swap_exact_wqms_for_tokens(self, amount_in: int, amount_out_min: int, targets: List[str], deadline: int = None) -> str:
        """Swap WQMS -> tokens (WQMS is an ERC20 token, needs approval)"""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # Approve WQMS for the exact amount
        self.ensure_allowance('WQMS', self.router.address, amount_in)
        
        checksum_path = [self.wqms.address] + [Web3.to_checksum_address(addr) for addr in targets]
        
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            checksum_path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
        })
        
        return self.send_transaction(tx)
    
    def swap_exact_tokens_for_wqms(self, amount_in: int, amount_out_min: int, sources: List[str], deadline: int = None) -> str:
        """Swap tokens -> WQMS (WQMS is an ERC20 token, needs approval)"""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # Approve the exact amount of input token (first token in path)
        self.ensure_allowance(sources[0], self.router.address, amount_in)
        
        checksum_path = [Web3.to_checksum_address(addr) for addr in sources] + [self.wqms.address]
        
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            checksum_path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
        })
        
        return self.send_transaction(tx)
    
    def add_liquidity(self, token_a: str, token_b: str, amount_a: int, amount_b: int = None,
                      amount_a_min: int = None, amount_b_min: int = None, deadline: int = None) -> str:
        """Add liquidity to a token pair. If amount_b is None, calculate from pool price."""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # Auto-calculate amount_b from pool price if not provided
        if amount_b is None:
            try:
                # Find the pool for this token pair
                pool_addr = None
                pool_name = None
                for name, addr in POOLS.items():
                    pair = pool_to_pairs(name)
                    if set(pair) == set([token_a, token_b]):
                        pool_addr = addr
                        pool_name = name
                        break
                
                if pool_addr is not None:
                    # Get pool contract
                    pool_contract = self.pool_contracts[pool_name]
                    
                    # Get token0 and token1 from pool
                    token0_addr = pool_contract.functions.token0().call()
                    token1_addr = pool_contract.functions.token1().call()
                    
                    # Get reserves
                    reserve0, reserve1, _ = pool_contract.functions.getReserves().call()
                    
                    # Convert to checksum addresses
                    token0_addr = Web3.to_checksum_address(token0_addr)
                    token1_addr = Web3.to_checksum_address(token1_addr)
                    
                    # Determine which token is token0 vs token1 in our pair
                    token_a_addr = Web3.to_checksum_address(TOKENS[token_a])
                    token_b_addr = Web3.to_checksum_address(TOKENS[token_b])
                    
                    # Identify pool token symbols for decimal-aware math
                    def _sym(addr):
                        for s, a in TOKENS.items():
                            if Web3.to_checksum_address(a) == addr:
                                return s
                        return None
                    t0_sym = _sym(token0_addr)
                    t1_sym = _sym(token1_addr)
                    dec_a = self.get_decimals(token_a)
                    dec_b = self.get_decimals(token_b)
                    
                    # Human-readable reserves (decimal-aware)
                    res_a_human = Decimal(0)
                    res_b_human = Decimal(0)
                    if token0_addr == token_a_addr and token1_addr == token_b_addr:
                        res_a_human = Decimal(reserve0) / (Decimal(10) ** self.get_decimals(t0_sym or token_a))
                        res_b_human = Decimal(reserve1) / (Decimal(10) ** self.get_decimals(t1_sym or token_b))
                    elif token0_addr == token_b_addr and token1_addr == token_a_addr:
                        res_a_human = Decimal(reserve1) / (Decimal(10) ** self.get_decimals(t1_sym or token_a))
                        res_b_human = Decimal(reserve0) / (Decimal(10) ** self.get_decimals(t0_sym or token_b))
                    
                    print(f"Pool {pool_name}: reserveA={res_a_human} {token_a}, reserveB={res_b_human} {token_b}")
                    
                    # Calculate amount_b from pool price ratio (decimal-aware)
                    amount_a_human = Decimal(amount_a) / (Decimal(10) ** dec_a)
                    if res_a_human > 0 and res_b_human > 0:
                        amount_b_human = amount_a_human * res_b_human / res_a_human
                        amount_b = int(amount_b_human * (Decimal(10) ** dec_b))
                    else:
                        amount_b = amount_a
                    
                    print(f"Calculated amount_b: {amount_b} wei ({self.wei_to_human(amount_b, token_b)} {token_b})")
                    
                    # Cap at wallet balance (minus 1% buffer) so we never overdraw
                    bal_a = self.get_balance(token_a)
                    bal_b = self.get_balance(token_b)
                    if bal_a > 0 and amount_a > bal_a // 100 * 99:
                        print(f"Capping amount_a to balance: {self.wei_to_human(amount_a, token_a)} -> {self.wei_to_human(bal_a * 99 // 100, token_a)} {token_a}")
                        amount_a = bal_a * 99 // 100
                    if bal_b > 0 and amount_b > bal_b // 100 * 99:
                        print(f"Capping amount_b to balance: {self.wei_to_human(amount_b, token_b)} -> {self.wei_to_human(bal_b * 99 // 100, token_b)} {token_b}")
                        amount_b = bal_b * 99 // 100
                else:
                    # No pool found, use equal amounts
                    amount_b = amount_a
            except Exception as e:
                print(f"Could not get pool data: {e}, using equal amount")
                amount_b = amount_a
        
        # Retry logic for INSUFFICIENT_B_AMOUNT
        max_retries = 5
        min_amount = 1000  # minimum 1000 wei
        for attempt in range(max_retries):
            # Ensure minimum amounts
            if amount_a < min_amount:
                amount_a = min_amount
            if amount_b < min_amount:
                amount_b = min_amount
            
            # Calculate minimums AFTER capping: use 98% of the actual amounts
            if amount_a_min is None:
                amount_a_min = int(amount_a * 0.98)
            if amount_b_min is None:
                amount_b_min = int(amount_b * 0.98)
            
            # Approve both tokens (not native QMS)
            self.ensure_allowance(token_a, self.router.address, amount_a)
            if token_b != 'QMS':
                self.ensure_allowance(token_b, self.router.address, amount_b)
            
            # Convert addresses to checksum format
            token_a_addr = Web3.to_checksum_address(TOKENS[token_a])
            token_b_addr = Web3.to_checksum_address(TOKENS[token_b])
            
            # Build addLiquidity transaction
            tx = self.router.functions.addLiquidity(
                token_a_addr,
                token_b_addr,
                amount_a,
                amount_b,
                amount_a_min,
                amount_b_min,
                self.address,
                deadline
            ).build_transaction({
                'from': self.address,
            })
            
            try:
                return self.send_transaction(tx)
            except ContractLogicError as e:
                if "INSUFFICIENT_B_AMOUNT" in str(e) and attempt < max_retries - 1:
                    # Reduce amounts by half and retry
                    print(f"INSUFFICIENT_B_AMOUNT detected, retrying with reduced amounts (attempt {attempt+1}/{max_retries})")
                    amount_a = max(amount_a // 2, min_amount)
                    amount_b = max(amount_b // 2, min_amount)
                    continue
                else:
                    raise
        
        # If we got here, all retries failed (should not happen due to raise in loop)
        raise RuntimeError("Failed to add liquidity after multiple retries due to INSUFFICIENT_B_AMOUNT")

    def remove_liquidity(self, token_a: str, token_b: str, liquidity: int, amount_a_min: int = None, amount_b_min: int = None, deadline: int = None) -> str:
        """Remove liquidity and receive underlying tokens (via router)"""
        if deadline is None:
            deadline = int(time.time()) + 1200
        
        # Find the pool for this token pair
        pool_name = None
        for name, addr in POOLS.items():
            pair = pool_to_pairs(name)
            if set(pair) == set([token_a, token_b]):
                pool_name = name
                break
        
        if pool_name is None:
            raise ValueError(f"No pool found for {token_a}/{token_b}")
        
        # Get pool contract
        pool_contract = self.pool_contracts[pool_name]
        
        # Determine which token is token0 vs token1 in the pool
        token0_addr = pool_contract.functions.token0().call()
        token1_addr = pool_contract.functions.token1().call()
        token0_addr = Web3.to_checksum_address(token0_addr)
        token1_addr = Web3.to_checksum_address(token1_addr)
        
        token_a_addr = Web3.to_checksum_address(TOKENS[token_a])
        token_b_addr = Web3.to_checksum_address(TOKENS[token_b])
        
        # Build removeLiquidity transaction (via router)
        tx = self.router.functions.removeLiquidity(
            token_a_addr,
            token_b_addr,
            liquidity,
            amount_a_min,
            amount_b_min,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
        })
        
        return self.send_transaction(tx)


def print_balances(client: QMSClient):
    """Print all token balances"""
    print("\n=== Wallet Balances ===")
    for symbol in ['QMS', 'WQMS', 'USDT', 'USDC', 'WBTC', 'WETH']:
        try:
            bal = client.get_balance(symbol)
            human = client.wei_to_human(bal, symbol)
            print(f"  {symbol}: {human}")
        except Exception as e:
            print(f"  {symbol}: Error - {e}")
    print()


def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default"""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def get_user_int(prompt: str, default: int = None) -> int:
    """Get integer input from user"""
    while True:
        try:
            val = get_user_input(prompt, str(default) if default else None)
            return int(val)
        except ValueError:
            print("Please enter a valid integer")


def get_user_float(prompt: str, default: float = None) -> float:
    """Get float input from user"""
    while True:
        try:
            val = get_user_input(prompt, str(default) if default else None)
            return float(val)
        except ValueError:
            print("Please enter a valid number")


def get_user_choice(prompt: str, choices: List[str]) -> str:
    """Get user choice from list"""
    print(prompt)
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    while True:
        try:
            val = int(get_user_input("Select"))
            if 1 <= val <= len(choices):
                return choices[val - 1]
            print("Invalid choice")
        except ValueError:
            print("Please enter a valid number")


def ask_run_mode() -> str:
    """Ask whether to run single or batch mode"""
    return get_user_choice("Run mode?", ["Single run (ask each time)", "Multiple runs in a row", "Batch run (all at once)"])


def clear():
    """Clear terminal screen"""
    os.system('clear')
