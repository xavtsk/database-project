# PokéDB assessor setup using the team's cloud databases

This guide runs the web application on your computer using the team's existing Google Cloud MySQL database and MongoDB Atlas database. No local MySQL or MongoDB installation is needed. The databases already contain the project schema, catalogue and demonstration history.

The application server and browser run on your computer. Your computer reaches MySQL through its own SSH tunnel and reaches Atlas through the supplied MongoDB connection string. The student's computer does not need to stay switched on, but the cloud VM and Atlas cluster must remain available.

## 1. Information to obtain from the team

Before starting, obtain:

- The source ZIP, including backend, frontend, scripts, data and requirements.txt, or access to the private GitHub repository and the submission branch/commit.
- Confirmation that your Google account has been added to project `pokedex-project-512319` with the **Compute OS Login** and **Compute Viewer** roles. The account you use for Google Cloud sign-in must match the one the team authorised.
- A MySQL application username and password, supplied privately. This is separate from Google sign-in and MongoDB credentials.
- The complete Atlas MONGO_URI connection string and database name, supplied privately. The URI normally contains a database username and password. It must be copied exactly, including password URL encoding where needed.
- A team contact for access problems. Do not publish the credentials in screenshots, reports or source control.

| Setting | Project value |
| --- | --- |
| Google Cloud project ID | pokedex-project-512319 |
| VM | pokedex-mysql |
| Zone | us-west1-b |
| Local end of MySQL tunnel | 127.0.0.1:3308 |
| VM end of MySQL tunnel | 127.0.0.1:3306 |
| MySQL database | pokedex_battle |
| MongoDB database | pokedex_battle |
| Local application port | 5050 |

No cloud account billing or project creation is needed on your side.

## 2. Install the client tools

The steps below use Windows PowerShell. In VS Code choose Terminal > New Terminal and select PowerShell from the terminal profile menu. Run project commands from the extracted source folder containing requirements.txt, backend and scripts.

1. Install Python 3.13, the version used for the team's verification, from [python.org](https://www.python.org/downloads/windows/). Enable the installer option to add Python to PATH. Reopen the terminal and check:

   ```powershell
   python --version
   ```

2. Install the [Google Cloud CLI for Windows](https://docs.cloud.google.com/sdk/docs/install-sdk). Reopen the terminal and check:

   ```powershell
   gcloud --version
   ```

3. Extract the submitted source ZIP to a writable folder, such as `C:\Projects\database-project`. Open the extracted folder containing requirements.txt, backend and frontend. If cloning instead, use the branch/commit identified by the team.

4. From that source folder, create an isolated Python environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

The commands use the virtual environment's Python directly, so PowerShell script activation is not needed. VS Code, MySQL Workbench, MongoDB Compass, Node.js and Git are optional for running the app from the source ZIP. Browser internet access is needed for cloud connections and external sprites/fonts.

## 3. Create the private application configuration

In the source folder, create a file named exactly `.env.cloud`, without a `.txt` extension. Paste the settings below and replace the placeholders using the privately supplied credentials:

```dotenv
SQL_HOST=127.0.0.1
SQL_PORT=3308
SQL_USER="pokedex"
SQL_PASSWORD="MYSQL_PASSWORD_FROM_TEAM"
SQL_DATABASE=pokedex_battle
MONGO_URI="COMPLETE_ATLAS_CONNECTION_STRING_FROM_TEAM"
MONGO_DATABASE=pokedex_battle
FLASK_SECRET_KEY="PASTE_A_NEW_RANDOM_SECRET_HERE"
PORT=5050
```

Use the supplied MySQL username if it differs from `pokedex`. Remove or comment out any SQL_SOCKET entry. Keep the connection-string options supplied by the team. Do not use the local `mongodb://127.0.0.1:27017` example when connecting to Atlas.

Generate your own session secret and paste the result into FLASK_SECRET_KEY:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Save `.env.cloud`, then apply the cloud settings:

```powershell
Copy-Item .env.cloud .env -Force
```

This replaces any existing `.env`. The application reads `.env`, so repeat this copy whenever `.env.cloud` changes. Keep both files private and out of GitHub. The session secret is generated locally and is different from the database passwords.

## 4. Start the SSH tunnel in Terminal A

Open a separate local PowerShell terminal. Sign in with the Google account authorised by the team:

```powershell
gcloud auth login
gcloud config set project pokedex-project-512319
gcloud config set compute/zone us-west1-b
gcloud compute instances list --project=pokedex-project-512319
```

Sign in through the browser with the authorised account. If the installer already signed you in, check the active account with `gcloud auth list`. The instance list should show `pokedex-mysql` as `RUNNING`.

Start the tunnel:

```powershell
gcloud compute ssh pokedex-mysql --project=pokedex-project-512319 --zone=us-west1-b -- -N -L 127.0.0.1:3308:127.0.0.1:3306 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3
```

On the first use, follow gcloud's instructions to create your own SSH key. Use your own key; the team's private SSH key is not required. Verify a new server fingerprint with the team before accepting it. If the command requests a choice of SSH executable, follow the installed CLI's prompts.

A running tunnel often has no further output. Leave this terminal open. This command starts the tunnel on your computer; running it in browser Cloud Shell would forward a port in Cloud Shell instead.

In another local terminal, check the local port:

```powershell
Test-NetConnection 127.0.0.1 -Port 3308
```

`TcpTestSucceeded : True` confirms a local listener. The application health check below confirms that the database is actually reachable through it. If an older tunnel is already running, reuse it or stop your previous tunnel before starting another on port 3308.

## 5. Run the application in Terminal B

Open a second local PowerShell terminal in the source folder. Use a fresh terminal so previous test-account environment settings do not override `.env`.

```powershell
.\.venv\Scripts\python.exe scripts/run_local.py
```

Keep this terminal open as well. Open:

- Application: <http://127.0.0.1:5050>
- Database health: <http://127.0.0.1:5050/api/health>

Expected health response:

```json
{"mongodb":"ready","sql":"ready"}
```

Both terminals must stay running while using the application. On later visits, repeat the tunnel command in section 4 and the application command in section 5 only. Dependency installation, sign-in and configuration need not be repeated unless access expires or settings change.

## 6. Demonstrate the project

1. Create a labelled assessor demonstration trainer and select a starter. Profiles are local demonstration selections, not authenticated user accounts.
2. Browse the Pokédex and filter by name, ID or type.
3. Create/edit a team, choose four eligible distinct moves for each member and stay within the 30-point budget. Delete only a spare demonstration team.
4. Open Team analysis to inspect weaknesses, coverage and recommendations. A new collection may have no unused candidate until rewards are collected.
5. Start a manual or automatic battle, take a turn and reload to check saved-state recovery.
6. Inspect an existing completed battle and analytics. Use a team with one member and finish battles to create new 1v1 observations.
7. After a win, inspect the saved reward and reopen its history. The same reward should remain associated with the battle.

This connection uses the shared project data. Saves, deletions, battles and rewards change that data for everyone. Use the labelled demonstration trainer or a team-approved prepared profile. Do not edit or delete other users' teams.

Do not run `scripts.setup_databases`, data import/migration commands or opt-in integration tests against this shared demonstration connection. Existing cloud data is already initialised. Database construction and integration tests require a separately agreed test database/account; ask the team for isolated-test instructions if needed.

## 7. Troubleshooting

| Message or symptom | Action |
| --- | --- |
| `python` or `gcloud` not recognised | Reopen the terminal after installing the tool and check PATH |
| Google Cloud permission denied | Confirm gcloud signed in with the account authorised by the team. Ask the team to check OS Login, VM/project access and any service-account or organisation requirements |
| SSH connection timeout | Ask the team to check the VM is running, its SSH firewall rule and your network access |
| `Address already in use` on 3308 | A tunnel or another program already owns that local port. Reuse the intended tunnel or stop your older one |
| MySQL WinError 10061 / connection refused | Keep Terminal A open, check SQL_PORT=3308 and repeat the port check |
| MySQL `using password: NO` | Supply SQL_PASSWORD in `.env.cloud`, repeat `Copy-Item .env.cloud .env -Force`, and use a fresh app terminal with no SQL_PASSWORD override |
| MySQL error 1045 / access denied | Ask the team to verify the application account, password and allowed host |
| MySQL error 1044 | Confirm the account has privileges on pokedex_battle. Do not substitute the integration-test account |
| MongoDB timeout or authentication error | Confirm the exact supplied Atlas URI and MONGO_DATABASE. Ask the team to check cluster availability, database-user permissions and network access |
| Startup says terminal settings override `.env` | Open a fresh terminal and restart the app with the virtual environment Python command in section 5. Existing SQL/Mongo environment variables take priority |
| Port 5050 occupied | Reuse your existing app, or choose a different PORT in `.env.cloud`, copy it to `.env` again and update the browser URL |
| New profile has empty analytics | Use the agreed populated demo profile or complete actual battles |

For support, send the team the error and the health response, omitting `.env`, passwords, full Atlas URIs and private keys. To stop, press Ctrl+C in the app terminal, then Ctrl+C in the tunnel terminal.

## Reference documentation

- [Google Cloud CLI installation](https://docs.cloud.google.com/sdk/docs/install-sdk)
- [Google Cloud OS Login access requirements](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin)
- [Atlas driver connections](https://www.mongodb.com/docs/atlas/driver-connection/)
- [Atlas database users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/)

For instructions to create and populate your own independent databases, see [the user manual](user-manual.md).
