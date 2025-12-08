<div align="center">
  <a href="https://flare.network/" target="blank">
    <img src="https://content.flare.network/Flare-2.svg" width="300" alt="Flare Logo" />
  </a>
  <br />
  <a href="CONTRIBUTING.md">Contributing</a>
  ·
  <a href="SECURITY.md">Security</a>
  ·
  <a href="CHANGELOG.md">Changelog</a>
</div>

# Smart Accounts Cli

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
./smart_accounts.py ...
```

## help message
```sh
./smart_accounts.py --help
```

## `encode` command

This command encodes passed values into smart account instructions (xrpl
references)

```bash
./smart_accounts.py encode fxrp-cr -w 136 -v 1 -a 1 
# 0x0088000000000000000000010001000000000000000000000000000000000000
```

To see the list of all possible instructions you can run
```bash
./smart_accounts.py encode --help
```

## `bridge` command

This command provides functions for interacting with the bridge, like sending
instructions.


```bash
./smart_accounts.py bridge instruction 0x0045000000000000000000010001000000000000000000000000000000000000

```

This also supports passing values via stdin by passing `-` so command
composition like this is possible

```bash
./smart_accounts.py encode fxrp-cr -w 136 -v 1 -a 1 | ./smart_accounts.py bridge instruction -
# sent bridge request: 102B3C3B8064EBEEB9C7816CF75A920ED1B22FEF8B5B6244BD3CA2AE4DAA7C78
```
