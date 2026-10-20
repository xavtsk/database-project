# Windows setup with MySQL Server

The project now uses **MySQL Server** for relational data and **MongoDB** for battle data. MySQL Workbench is a client for running SQL; it does not by itself provide a database server.

This setup uses MySQL on **127.0.0.1:3307**, leaving the existing MariaDB service on port 3306. There is no need to uninstall MariaDB. All commands below work from the project root with Python installed.

## 1. Install and configure MySQL

Install **MySQL Community Server 8.4 LTS** using its Windows MSI package and MySQL Configurator. The supported minimum is 8.0.19 because the importer uses row aliases and the schema needs enforced CHECK constraints.

- [Official Windows installation guide](https://dev.mysql.com/doc/refman/8.4/en/windows-installation.html)
- [MySQL Community Server downloads](https://dev.mysql.com/downloads/mysql/)

In the configurator, select a development installation, TCP/IP port **3307**, set a root password and configure MySQL as a Windows service. Use a separate MySQL data directory; existing MariaDB data files cannot be reused as MySQL data files. The app launcher does not install MySQL or start its Windows service.

## 2. Open a MySQL Workbench connection

Create a connection with:

| Field | Value |
| --- | --- |
| Connection name | PokeDB MySQL |
| Hostname | 127.0.0.1 |
| Port | 3307 |
| Username | root |
| Password | The password chosen for the new MySQL Server |

Test the connection, open it, and run this in a query tab:

```sql
SELECT VERSION(), @@version_comment;
```

The result should identify MySQL, for example `8.4.x` and `MySQL Community Server - GPL`. If it identifies MariaDB, check the connection port. The root password belongs to this MySQL installation; it may differ from passwords for other database servers.

## 3. Create the project database and account

Run as root in Workbench. Replace the password placeholder with your own password before executing:

```sql
CREATE DATABASE IF NOT EXISTS pokedex_battle CHARACTER SET utf8mb4;
CREATE USER 'pokedex'@'localhost' IDENTIFIED BY 'choose-your-project-password';
GRANT ALL PRIVILEGES ON pokedex_battle.* TO 'pokedex'@'localhost';
```

If the project account already exists on this MySQL Server, use its existing password and run the GRANT statement. Creating a Workbench connection or entering a username in `.env` does not create an account or grant permissions.

Use the server's default `caching_sha2_password` authentication. The project's `PyMySQL[rsa]` requirement supplies the extra authentication support; root authentication does not need changing.

## 4. Configure the application

If `.env` does not already exist, copy the example from either Command Prompt or PowerShell:

```cmd
copy .env.example .env
```

Open `.env` in the editor and set:

```dotenv
SQL_HOST=127.0.0.1
SQL_PORT=3307
SQL_USER=pokedex
SQL_PASSWORD="choose-your-project-password"
SQL_DATABASE=pokedex_battle
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DATABASE=pokedex_battle
FLASK_SECRET_KEY=replace-with-a-random-secret
PORT=5050
```

Use a password matching the actual MySQL project account. Generate a session secret with `python -c "import secrets; print(secrets.token_hex(32))"` and paste it into `.env`. This file stays ignored by Git. Credentials are never entered in the terminal command line or committed to the repository.

If your MySQL installation uses another port, set `SQL_PORT` and the Workbench port to that value. The project defaults to 3307 for this computer's two-server setup.

## 5. Install dependencies and import data

```cmd
python -m pip install -r requirements.txt
python -m scripts.setup_databases
```

Setup loads `.env`, checks that the server is MySQL, creates tables, imports the cached catalogue and prepares MongoDB. It upserts source data and preserves application data. Both database services must be running.

To create and inspect the MySQL tables before MongoDB is available:

```cmd
python -m scripts.setup_databases --sql-only
```

This creates the real MySQL catalogue and relational schema. Run full setup when MongoDB is ready; the browser application needs both databases. The existing raw Pokémon files are reused. `--fetch-dark` is an optional download for a missing Dark-type cache file only.

## 6. Start the browser app

```cmd
python scripts/run_local.py
```

With `PORT=5050`, open **http://127.0.0.1:5050**. A connection error should be checked against the running MySQL service, port and project-account permissions. Restart the app after changing `.env` or reimporting catalogue data.

## Testing and existing data

Offline checks: `python -m unittest discover -s tests -v`.

Live integration tests need MySQL and MongoDB plus a separate test account authorized to create/drop uniquely named test databases. The normal project account is scoped to `pokedex_battle` and is not sufficient for that suite. Load test credentials into environment variables and set `RUN_DB_TESTS=1`. Do not broaden the normal account's grants just to run tests.

This switch creates a new MySQL database; it does not migrate any existing MariaDB trainers, owned Pokémon or teams. Existing MongoDB logs retain their SQL IDs, so an existing installation with trainer/history data needs a reviewed migration preserving those IDs before pointing those logs at a fresh SQL database. For a fresh local setup, start with an unused database name for MongoDB if an older installation's battle data is present.

References: [PyMySQL authentication support](https://pymysql.readthedocs.io/en/latest/user/installation.html), [MySQL row-alias upserts](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html).
