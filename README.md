<p align="left">
  <a href="https://flare.network/" target="blank"><img src="https://content.flare.network/Flare-2.svg" width="410" height="106" alt="Flare Logo" /></a>
</p>

# smart-accounts-cli

A python tool to interact with [`flare-smart-accounts`](https://github.com/flare-foundation/flare-smart-accounts) in a sandbox environment.

# Setting up and using the cli

1. installing dependencies
2. setting up `.env` file

## Installing dependencies

Creating a simple python virtual environment and installing dependencies is enough:

```sh
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Setting up `.env` file

Create the environment file using the provided example

```sh
cp .env.example .env
```

Open the created `.env` in your editor of choice and fill out the values.

# Using the cli

You can then run the script with the command:

```sh
./smart_accounts ...
```

## help message
```sh
./smart_accounts --help
```


## `bridge` command

The `bridge` command executes an XRPL transaction with instructions for one of the actions, determined by the positional argument provided.
A payment transaction with the appropriate memo field value is sent to the operator's XRPL address from the XRPL address specified in the `.env` file.

What follows is a list of possible positional arguments, what they do, and the additional parameters of each.

### `deposit`

Deposit an `amount` of FXRP from the smart account belonging to the XRPL address to the Firelight vault, designated by the `MasterAccountController` contract.

```sh
./smart_accounts.py bridge deposit -a <amount>
```

### `withdraw`

Begin the withdrawal process from the Firelight vault.
An `amount` of FXRP is marked to be withdrawn from the Firelight vault to the user's smart account.

```sh
./smart_accounts.py bridge withdraw -a <amount>
```

### `redeem`

Redeem a `lots` amount of FXRP.
That number of lots of FXRP are burned from the user's smart account, and the same amount of XRP is sent to the user's address on XRPL.

```sh
./smart_accounts.py bridge redeem -l <lots>
```

### `mint`

Mints a number of `lots` of FXRP to the user's smart account.
The script first reserves collateral with the agent with the `address`, by sending a `reserveCollateral` instruction.
It then sends a `lots` amount of XRP to the agent's underlying address.
An executor, determined by the `MasterAccountController`, will complete the minting process, and `lots` of FXRP will be minted to the user's smart account.

If you are unsure about the agent address you should use `0x55c815260cBE6c45Fe5bFe5FF32E3C7D746f14dC` on coston2.

```sh
./smart_accounts.py bridge mint -a <address> -l <lots>
```

### `claim-withdraw`

Complete the withdrawal process from the Firelight vault by claiming the funds.
After the withdrawal process has been started, the funds are locked for a certain amount of time.
Once that period has passed, they can be transferred back to the user's smart account.

```sh
./smart_accounts.py bridge claim-withdraw
```

### `custom`

Execute a custom action on the Flare chain.
Make a transaction to the `address`, paying the `value`, and attaching the `calldata`.
The `calldata` is the encoding of a function and its argument values, on the smart contract at the `address.

```sh
./smart_accounts.py bridge deposit -a <address> -v <value> -d <calldata>
```

Before making a transaction on XRPL with the necessary instructions, this command performs an additional step.
It first packs the three provided values (`address`, `value`, and `calldata`) into a `IMasterAccountController.CustomInstruction` struct.
Then, it calls the `registerCustomInstruction` function of the `MasterAccountController` contract, with the former as an argument.

Thus, it both registers a custom instruction with the `MasterAccountController` contract and retrieves the required `callHash`, which it can then send to the operator's XRPL address as instructions.

## `debug` command

The `debug` command offers some utility options for running the CLI.
It allows three positional arguments: `mock-custom`, `check-status`, and `simulation`.

### `mock-custom`

Simulate a custom instruction with the mock `MasterAccountController` contract.
Instead of sending the instructions as a transaction on XRPL and bridging them to Flare, the custom instructions are sent to the `MasterAccountController` contract directly.

The `address`, `value`, and `data` parameters are the same as for the custom positional argument.
The `seed` is a string representing an XRPL account.

```sh
./smart_accounts.py debug mock-custom -s <seed> -a <address> -v <value> -d <calldata>
```

### `check-status`

Check the status of the XRPL transaction with the `xrpl_hash`.

```sh
./smart_accounts.py debug check-status <xrpl_hash>
```

### `simulation`

Run the simulation of the FAsset cycle.
It converts `mint` lots of XRP to FXRP, deposits `deposit` FXRP into the Firelight vault, withdraws `deposit` FXRP back to the smart account, and finally redeems `mint` FXRP back to XRP.

```sh
./smart_accounts.py debug simulations -a <address> -m <mint> -d <deposit>
```

This is equivalent to running the following commands:

```sh
./smart_accounts.py bridge mint -a <address> -l <mint>
./smart_accounts.py bridge deposit -a <deposit>
./smart_accounts.py bridge withdraw -a <deposit>
./smart_accounts.py bridge claim-withdraw
./smart_accounts.py bridge redeem -l <mint>
```
