# QMS Testnet Farming Bot

Automated swap and liquidity farming bot for **QMS Testnet** (Chain ID: `19480`) using the QWAP.xyz router.

## Disclaimer

This bot interacts with blockchain smart contracts and handles a private key. Use at your own risk.
- Only use on **testnet** with test funds.
- Never commit your `.env` file.
- The author is not responsible for any loss of funds.

## Features

- **Wrap QMS to WQMS** (single or batch mode, sequential/random order)
- **Swap tokens** via QWAP.xyz router (multi-token, batch mode)
- **Add liquidity** to supported pools (batch mode)
- **Remove liquidity** - NOT YET IMPLEMENTED (planned for a future release)
- **Check balances** for all configured tokens
- **Check failed transactions** via `check_tx.py` (wallet address can be overridden via CLI argument or by editing `WALLET_ADDRESS`)
- Human-readable amounts (0.01, 0.1, 1, 11, etc.)
- All config loaded from `.env`

## Requirements

- Python 3.12+
- web3
- python-dotenv
- QMS Testnet funds (for gas + operations)

Install dependencies:

    pip install web3 python-dotenv

## Setup

1. Clone the repo

       git clone <your-repo-url>
       cd qms-farming

2. Copy environment template

       cp .env.example .env

3. Edit `.env` and set your wallet private key:

       PRIVATE_KEY=0xYourPrivateKeyHere

   Never share or commit this file. It is already listed in `.gitignore`.

4. Run the bot

       python3 farming_bot.py

## Configuration (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| CHAIN_ID | Network chain ID | 19480 |
| RPC_URL | RPC endpoint | https://rpc.testnet.qms.finance |
| CURRENCY_SYMBOL | Native currency symbol | QMS |
| BLOCK_EXPLORER | Block explorer URL | https://testnet.qmsscan.io |
| ROUTER_ADDRESS | QWAP.xyz router address | 0x93AFF45f28e5DF1b55f5AEFEfB807De843b12619 |
| PRIVATE_KEY | Wallet private key (secret) | 0x... |
| USDT, USDC, WBTC, WQMS, WETH | Token contract addresses | See .env.example |
| POOL_* | Liquidity pool addresses | See .env.example |

## Menu Options

### 1. WRAP QMS to WQMS
Convert native QMS into WQMS token.
- Single run: input amount each time
- Batch mode: base amount + repetitions + order (Sequential / Random)

### 2. SWAP tokens
Swap tokens via the router.
- Single run: manual input each time
- Batch mode: base amount + repetitions + order mode

### 3. ADD LIQUIDITY
Provide liquidity to a pool.
- Single run: manual input each time
- Batch mode: select pool + amount + repetitions + order mode

### 4. Check Balances
Display balances for all configured tokens.

### 5. REMOVE LIQUIDITY - NOT YET IMPLEMENTED
This feature is not yet implemented. It is planned for a future release.

- Currently, selecting this option will not perform any on-chain action.
- If you need this feature urgently, feel free to open an issue or submit a PR.

### 6. Exit
Quit the bot.

Note: Menu numbering may vary depending on the current build of `farming_bot.py`.

## Example Session

    1. WRAP QMS -> WQMS
    2. SWAP tokens
    3. ADD LIQUIDITY
    4. Check Balances
    5. REMOVE LIQUIDITY   (not yet implemented)
    6. Exit

## Checking Transaction Status (check_tx.py)

The `check_tx.py` script searches for **failed addLiquidity transactions** sent from a specific wallet to the router.

### Usage

    # Use the default wallet defined inside check_tx.py
    python3 check_tx.py

    # Check a different wallet (override via argument)
    python3 check_tx.py 0xWalletAddressHere

    # Limit how many blocks are scanned backwards
    python3 check_tx.py 0xWalletAddressHere --limit=5000

### Changing the Wallet Address

By default, the wallet address that is checked comes from the `WALLET_ADDRESS` variable inside `check_tx.py`.

Two ways to change it:

1. **Quick way (no file edit):** pass the wallet as the first CLI argument

       python3 check_tx.py 0xb50b87Cca4FD3cC57Bf253507aBF09cEDE3072a1

2. **Permanent way:** edit `check_tx.py` and find the line:

       WALLET_ADDRESS = "0xb50b87Cca4FD3cC57Bf253507aBF09cEDE3072a1"

   Replace it with the wallet you want to inspect.

> **Note:** `ROUTER_ADDRESS` and `RPC_URL` are read automatically from `.env`, so you do not need to edit them unless you change the router or RPC endpoint.

## Project Structure

    qms-farming/
    |-- farming_bot.py    # Main interactive bot
    |-- qms_client.py     # Web3 client wrapper
    |-- check_tx.py       # Failed transaction checker (addLiquidity)
    |-- demo.py           # Demo / testing script
    |-- .env.example      # Environment template (safe to commit)
    |-- .gitignore        # Ignores .env, __pycache__, etc.
    |-- README.md

## Roadmap

- [x] Wrap QMS to WQMS
- [x] Swap tokens
- [x] Add liquidity
- [x] Check balances
- [x] Check failed transactions (`check_tx.py`)
- [ ] Remove liquidity - planned
- [ ] Portfolio summary / PnL
- [ ] Config file for pool presets

## Security Notes

- `.env` is gitignored - never commit it.
- `.env.example` contains no real secrets - safe to commit.
- Use a dedicated testnet wallet, not your main wallet.
- Rotate the private key immediately if it ever leaks.

## Notes

- Slippage tolerance: 1 percent
- Deadline: 20 minutes from tx creation
- Test mode is available when no private key is set

## License

MIT
