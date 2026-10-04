import os
from web3 import Web3
from dotenv import load_dotenv
load_dotenv('/root/qms-farming/.env')
w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL', 'https://rpc.testnet.qms.finance')))

# Find most recent failed addLiquidity tx from the wallet
addr = '0xb50b87Cca4FD3cC57Bf253507aBF09cEDE3072a1'
router = '0x93AFF45f28e5DF1b55f5AEFEfB807De843b12619'

# Scan recent blocks for our txs to router
best = None
latest = w3.eth.block_number
for bn in range(latest, latest - 80, -1):
    try:
        block = w3.eth.get_block(bn)
        for txh in block['transactions']:
            try:
                tx = w3.eth.get_transaction(txh)
            except Exception:
                continue
            if tx['from'] == addr and tx.get('to') and Web3.to_checksum_address(tx['to']) == router:
                rcpt = w3.eth.get_transaction_receipt(txh)
                if rcpt.status == 0:
                    best = txh
                    break
        if best:
            break
    except Exception:
        continue

if not best:
    print('No recent failed router tx found')
    exit()

tx = w3.eth.get_transaction(best)
print('Tx:', best)
print('Selector:', tx['input'].hex()[:10])

data = tx['input'].hex()
def field(i):
    start = i*64
    return data[start:start+64]

# addLiquidity: (tokenA, tokenB, amountA, amountB, minA, minB, to, deadline)
tok_a = '0x' + field(1)[24:]
tok_b = '0x' + field(2)[24:]
amt_a = int(field(3), 16)
amt_b = int(field(4), 16)
min_a = int(field(5), 16)
min_b = int(field(6), 16)

tokens = {k: v for k, v in {
    'USDT': os.getenv('USDT'),
    'USDC': os.getenv('USDC'),
    'WBTC': os.getenv('WBTC'),
    'WQMS': os.getenv('WQMS'),
    'WETH': os.getenv('WETH'),
}.items()}
def name(a):
    for k,v in tokens.items():
        if Web3.to_checksum_address(v) == Web3.to_checksum_address(a):
            return k
    return a

na, nb = name(tok_a), name(tok_b)
dec = lambda sym: int(client_dec(sym)) if False else None

# Get decimals on chain
ERC20_ABI = [{'constant':True,'inputs':[],'name':'decimals','outputs':[{'name':'','type':'uint8'}],'type':'function'}]
def decimals(sym):
    c = w3.eth.contract(address=Web3.to_checksum_address(tokens[sym]), abi=ERC20_ABI)
    return c.functions.decimals().call()

print(f'\nTokenA: {na}, TokenB: {nb}')
print(f'amountA = {amt_a} wei = {amt_a/10**decimals(na):.10f} {na}')
print(f'amountB = {amt_b} wei = {amt_b/10**decimals(nb):.10f} {nb}')
print(f'minA    = {min_a} wei = {min_a/10**decimals(na):.10f} {na}')
print(f'minB    = {min_b} wei = {min_b/10**decimals(nb):.10f} {nb}')

# Pool reserves
POOL_ABI = json_abi = [
    {'inputs':[],'name':'getReserves','outputs':[{'name':'','type':'uint112'},{'name':'','type':'uint112'},{'name':'','type':'uint32'}],'stateMutability':'view','type':'function'},
    {'inputs':[],'name':'token0','outputs':[{'name':'','type':'address'}],'stateMutability':'view','type':'function'},
    {'inputs':[],'name':'token1','outputs':[{'name':'','type':'address'}],'stateMutability':'view','type':'function'},
]
import json as _json
POOL_ABI = _json.loads('''[{"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]''')

pools = {k: v for k,v in {
    'USDT_WBTC': os.getenv('POOL_USDT_WBTC'),
    'WQMS_WBTC': os.getenv('POOL_WQMS_WBTC'),
    'WQMS_WETH': os.getenv('POOL_WQMS_WETH'),
    'WETH_USDC': os.getenv('POOL_WETH_USDC'),
    'WQMS_USDC': os.getenv('POOL_WQMS_USDC'),
    'USDT_WQMS': os.getenv('POOL_USDT_WQMS'),
}.items() if v}
from qms_client import pool_to_pairs
for pname, paddr in pools.items():
    if set(pool_to_pairs(pname)) == {na, nb}:
        pc = w3.eth.contract(address=Web3.to_checksum_address(paddr), abi=POOL_ABI)
        r0, r1, _ = pc.functions.getReserves().call()
        t0 = Web3.to_checksum_address(pc.functions.token0().call())
        t1 = Web3.to_checksum_address(pc.functions.token1().call())
        n0, n1 = name(t0), name(t1)
        d0, d1 = decimals(n0), decimals(n1)
        print(f'\nPool {pname}: {n0}={r0/10**d0:.8f} / {n1}={r1/10**d1:.8f}')
        # Optimal ratio
        if na == n0:
            opt_b = (amt_a/10**decimals(na)) * (r1/10**d1) / (r0/10**d0)
        else:
            opt_b = (amt_a/10**decimals(na)) * (r0/10**d0) / (r1/10**d1)
        print(f'Optimal B for amountA = {opt_b:.10f} {nb}')
        print(f'sent B = {amt_b/10**decimals(nb):.10f} {nb}')
        break
