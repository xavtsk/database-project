# Low-cost shared MySQL on Google Cloud

The selected plan is one Google Compute Engine VM for MySQL. MongoDB stays on
Atlas. Each teammate runs the Flask app locally and connects to MySQL through
an SSH tunnel. The website itself is still a local demonstration.

## Status

The existing MySQL database has a preparation backup under ignored
`.local/backups/mysql-before-cloud-20261021T200735135266Z/`. It contains 15 base
tables and three views, including the existing trainer, five teams, 36 owned
Pokémon and 35 reward records. Its `manifest.json` records counts and a SHA-256
checksum. Take another export while the app is stopped immediately before the
actual migration; this preparation backup is not an ongoing backup service.

On 22 October 2026 the VM `pokedex-mysql` was created in project
`pokedex-project-512319`, zone `us-west1-b`. The owner confirmed that MySQL
Community Server 8.4.13 is installed and its service is active. The owner also
verified the running server's loopback bind address, 128 MB buffer pool,
25-connection limit and disabled Performance Schema. Windows OpenSSH connects
successfully to the VM using the development key. The MySQL import is complete:
all 60,145 rows across 15 tables match the exported source snapshot, the next
auto-increment values match the SQL dump, and all three views are queryable.

The development computer's private `.env` now uses the VM through the SSH tunnel
on `127.0.0.1:3308`, with a new project-account password. Atlas settings were
preserved. The previous `.env` is backed up privately as `env-before-cloud.env`
inside the transfer backup directory. The local MySQL database remains intact.

The 65 old MongoDB battles have already been copied to Atlas. App checks against
the actual cloud databases passed for the Pokédex, 36 owned Pokémon, five teams,
team analysis/recommendations, battle history, analytics and 1v1 matchups. Atlas
analytics reports 65 battles: 35 wins and 30 losses. The history endpoint returns
the latest 50 by design. See the [verification record](../progress-report/google-cloud-mysql-verification.md).

## Daily use on the development computer

From the project root, run this in one Command Prompt or PowerShell terminal:

```text
.\.local\gcp\start-tunnel.cmd
```

Leave that terminal open. If the tunnel is already listening on port 3308, the
launcher reports that and exits without starting another connection. A tunnel
started by this launcher automatically reconnects five seconds after SSH exits;
press Ctrl+C to stop it. In another terminal run the private clean launcher:

```text
.\.local\gcp\run-cloud.cmd
```

Open `http://127.0.0.1:5050`. Local Windows MySQL/MongoDB services are no longer
needed for this cloud configuration; the VM, Atlas and the SSH tunnel must be
available. The ignored launcher/key files belong to this development computer.
Teammates need their own SSH keys, OS Login access and project database users;
use the connection instructions below rather than sharing a private key.

The clean launcher clears inherited SQL/MongoDB connection variables for its
child process so the saved `.env` is used. It does not change the parent
terminal, `.env` or `PORT`. The normal `python -m scripts.run_local` entry point
continues to respect environment-variable overrides and now warns when their
connection values differ from `.env`, printing key names only. Startup errors
identify MySQL authentication/tunnel failures or MongoDB connection failures
without echoing connection strings or passwords. An interrupted tunnel does not
require database setup to be rerun.

### Navigation speed

The app reuses up to four MySQL connections per Flask process. Each checkout is
exclusive. Standalone reads use autocommit, avoiding a separate `COMMIT` network
trip. Grouped writes explicitly `BEGIN` and return their connection only after
commit. Failed operations roll back and discard their connection. Standalone
reads retry once for MySQL disconnect codes 2006/2013; writes and other errors
are never automatically replayed. Idle connections are checked before reuse
after 30 seconds. Command-line scripts still close their own connections
normally. Restart the app after changing SQL credentials.

Team analysis loads the saved-team list without downloading the collection's
full move data. It displays statistics and type coverage while recommendations
finish separately. Recommendations are still calculated by MySQL and supported
by MongoDB battle evidence; no mutable team/collection results are cached. A
saved team and its selected moves load through one ownership-filtered JOIN.
Team saves batch the member inserts before batching their moves, within the
same transaction. The browser keeps up to 20 successful Pokédex responses until
refresh, so returning to a visited catalogue page avoids another request.
Profile-specific teams, collections, battles and analytics still load fresh.

On 22 October, paired read-only checks with a warm catalogue measured the
analysis endpoint at 17.22 seconds with fresh connections versus 4.48 seconds
with reuse. Recommendations took 9.39 versus 2.99 seconds. All five compared
endpoint response hashes matched. These are individual request timings, not
browser navigation guarantees. The first catalogue load and requests after an
idle period can take longer, and the Oregon connection still adds latency.

A second pass reduced remaining network trips. Compared with the initial pool,
the same read-only checks measured saved teams at 1.67 to 0.60 seconds,
collection at 1.66 to 0.77 seconds, team analysis at 4.72 to 1.36 seconds, and
battle history at 0.84 to 0.28 seconds. All 14 paired API response hashes matched.
Temporary MySQL tables verified commit/rollback and batched insert ordering;
no player tables were changed by those checks. Timings vary with the connection
and exclude browser rendering, animations and the initial catalogue load.

Do not restore the old local connection after new cloud gameplay without also
migrating the newer SQL records. Atlas logs and SQL ownership/reward IDs must
continue to refer to the same data.

## 1. Select the project

Open Google Cloud Console and click the project picker in the top bar. The
project ID appears in the picker or on the Welcome page. Use the project ID,
not the display name or numeric project number. Billing must be enabled.

There is no Google Cloud CLI installed on the development computer yet. The
first VM can be created in the console or in the console's Cloud Shell, where
the CLI is already available. Creating cloud resources requires signing in to
the intended Google account; a project ID alone does not grant access.

## 2. Create one VM

In **Compute Engine → VM instances → Create instance**, use:

| Setting | Value |
| --- | --- |
| Name | `pokedex-mysql` |
| Region | Oregon, `us-west1` |
| Zone | `us-west1-b`, or another available Oregon zone |
| Series and machine | E2, `e2-micro` (1 GB memory) |
| Provisioning | Standard, rather than Spot |
| OS | Ubuntu 24.04 LTS, x86/64-bit |
| Boot disk | **Standard persistent disk**, 30 GB |
| Public IPv4 | One; charged separately |
| HTTP/HTTPS firewall options | Leave off; this VM hosts MySQL |

Alternatively, these commands run in **Google Cloud Shell (Bash)**. Replace
`YOUR_PROJECT_ID` before running. The create command provisions a billable
resource, with eligible compute and disk usage offset by free-tier allowances.

```bash
gcloud services enable compute.googleapis.com --project=YOUR_PROJECT_ID
gcloud compute instances create pokedex-mysql \
  --project=YOUR_PROJECT_ID \
  --zone=us-west1-b \
  --machine-type=e2-micro \
  --provisioning-model=STANDARD \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-type=pd-standard \
  --boot-disk-size=30GB \
  --no-service-account \
  --no-scopes \
  --metadata=enable-oslogin=TRUE
```

The free tier applies to eligible monthly usage of one `e2-micro` in Oregon,
Iowa or South Carolina and up to 30 GB-months of standard persistent disk.
Balanced/SSD disks and Singapore compute do not qualify for that offer. Public
IPv4 currently costs US$0.005/hour (about US$3.65 for 730 hours), and data
transfer, snapshots and taxes can add charges. Check the console estimate and
set a billing budget alert; an alert does not impose a spending cap.

If a Cloud SQL instance was created while exploring options, it is a separate
resource with separate charges. Creating this VM does not replace or stop it.

## 3. Install and tune MySQL

Open the VM's **SSH** connection. Install MySQL Community Server **8.4 LTS**
using the official MySQL APT repository, selecting the 8.4 LTS release series.
Ubuntu's package named `default-mysql-server` is not a portable way to select
MySQL; do not substitute MariaDB.

For the 1 GB machine, start conservatively with an InnoDB buffer pool of
128 MB, `max_connections=25`, 16 MB temporary table limits and a modest table
cache. Leave MySQL bound to `127.0.0.1:3306`. A swap file can help during package
installation but does not replace RAM. Validate the configuration and check
`systemctl status mysql` and `SELECT VERSION(), @@version_comment` before import.

After installing MySQL, run the following in the **VM's SSH terminal**. This
creates a dedicated project configuration file on the fresh Ubuntu VM:

```bash
sudo tee /etc/mysql/mysql.conf.d/zz-pokedex.cnf >/dev/null <<'EOF'
[mysqld]
bind-address=127.0.0.1
mysqlx-bind-address=127.0.0.1
innodb_dedicated_server=OFF
innodb_buffer_pool_size=128M
max_connections=25
table_open_cache=256
tmp_table_size=16M
max_heap_table_size=16M
performance_schema=OFF
EOF

sudo mysqld --validate-config &&
sudo systemctl restart mysql &&
sudo systemctl is-active mysql
```

This also disables MySQL's Performance Schema instrumentation to reduce memory
overhead. The app's SQL views and battle analytics do not depend on Performance
Schema. MySQL's normal transaction and crash-recovery settings remain enabled.

Check that the **running server** picked up the limits:

```bash
sudo mysql -u root -p -e "SHOW VARIABLES WHERE Variable_name IN ('version','bind_address','mysqlx_bind_address','innodb_buffer_pool_size','max_connections','performance_schema');"
free -h
```

Enter the VM MySQL root password at its prompt. If root was configured for local
socket authentication without a password, omit `-p`. Expected values include
version 8.4.x, loopback bind addresses, buffer pool size `134217728`, maximum
connections `25` and Performance Schema `OFF`. If validation or restart fails,
inspect `sudo journalctl -u mysql -n 40 --no-pager` before continuing the import.

Use separate project database credentials, keeping administrator credentials
out of the application's `.env`. Provide each teammate their own database user
and SSH access. With OS Login, the project owner must grant the appropriate OS
Login permissions; database credentials alone do not grant SSH access.

## 4. Copy the current database

### Prepared transfer package

A fresh export was prepared on 22 October 2026 while the local app was stopped.
Read locks held the 15 source tables stable during export and content hashing;
no source records were changed. The snapshot contains 60,145 rows and three
views. The private local copy is under
`.local/backups/mysql-cloud-transfer-20261022T075756892281Z/`.

The restore package was uploaded over SSH into the VM user's private directory
`~/pokedex-migration-20261022T075756892281Z/`. The uploaded SQL file's SHA-256
matches the local file. It includes a new, project-scoped MySQL account with a
generated password held locally in ignored `.local/gcp/cloud-mysql-credentials.json`.
That password must not be pasted into chat or committed. The package's
`restore.sql` contains the provisioning statements, so its permissions are 600
inside a directory with permissions 700.

The VM owner runs this command in the **VM's SSH terminal** and enters the VM's
MySQL root password at the prompt:

```bash
bash ~/pokedex-migration-20261022T075756892281Z/import.sh
```

The script verifies the package checksum before importing. Its initial
`CREATE DATABASE` and `CREATE USER` statements deliberately fail if those names
already exist; it is intended for the fresh VM and does not overwrite an
existing project database. It writes `import.complete` only after the MySQL
client succeeds. If an import fails, keep the app stopped and review the error
before rerunning; MySQL DDL is not rolled back as one transaction.

After import, establish the SSH tunnel and run
`python .local/gcp/verify_mysql_transfer.py` on the development computer. It
compares every table's ordered row-content hash against the locked source
snapshot, compares next auto-increment values with the exported `CREATE TABLE`
definitions, and queries all three views. SQL dump definitions are used for the
ID comparison because `INFORMATION_SCHEMA` can cache older statistics. This
verification passed before `.env` was switched. These helpers and credentials
stay in ignored `.local/`; they are operational files, not application dependencies.

### Export/import approach

Stop gameplay before the final export so MySQL rewards and Atlas battle logs
do not change midway through the migration. Keep the original database as a
fallback.

Export all application tables and views together with `mysqldump`, using
`--single-transaction --quick --no-tablespaces --set-gtid-purged=OFF
--column-statistics=0 --hex-blob --default-character-set=utf8mb4
--skip-add-drop-table`. Use a temporary client option file for credentials;
do not put a password in a command-line argument. Export only the project
database, not MySQL's account/system databases.

Import into a fresh project database on the VM. The source server reports
26.7.0, so test the logical dump against the selected 8.4 server before switching
the app. Review view definers and create the intended database users explicitly.
Preserve all explicit IDs, constraints and auto-increment settings. Compare
table contents/counts, the three analysis views and trainer/reward references
with the source before using the cloud copy. Do not recreate starter accounts
or replace the migrated data by seeding a fresh player database.

## 5. Connect through SSH

Keep MySQL port 3306 closed to public internet traffic. Each teammate needs
their own SSH access. The development computer has Windows OpenSSH installed,
so a local Google Cloud CLI installation is optional. Its dedicated development
key is in ignored `.local/gcp/pokedex_ed25519`; access to the private key file
is restricted to the current Windows user. Do not share that private key.

The ignored `.local/gcp/register-public-key.sh` contains the public-key
registration command for the selected project. Run its contents in **Google
Cloud Shell**, where `gcloud` is authenticated, rather than in the VM's SSH
terminal. It registers the public key with OS Login and prints the OS Login
username and VM external IP. OS Login IAM permissions are still required.

Once registered, the development computer can use Windows OpenSSH:

```text
ssh -i .local/gcp/pokedex_ed25519 -N -L 127.0.0.1:3308:127.0.0.1:3306 YOUR_OS_LOGIN_USERNAME@YOUR_VM_EXTERNAL_IP
```

Replace the username/IP with the values from Google Cloud. On the first
connection, verify the server host key using the VM's SSH console; its Ed25519
fingerprint is shown by `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.
Each teammate should generate and register their own key. A stopped/restarted
VM can receive a different ephemeral external IP, so check its current address
if connecting stops working.

Alternatively, with the Google Cloud CLI installed and authenticated on a
teammate's computer, start a tunnel in one terminal:

```text
gcloud compute ssh pokedex-mysql --project=YOUR_PROJECT_ID --zone=us-west1-b -- -N -L 127.0.0.1:3308:127.0.0.1:3306
```

Leave that terminal open. Port 3308 avoids the development computer's existing
MySQL and MariaDB ports. In the private `.env`, change the SQL connection only
after migration verification:

```dotenv
SQL_HOST=127.0.0.1
SQL_PORT=3308
SQL_USER=your-project-database-user
SQL_PASSWORD="your-project-database-password"
SQL_DATABASE=pokedex_battle
```

Clear any `SQL_SOCKET` setting and old SQL environment-variable overrides in
the app terminal. Keep the existing Atlas `MONGO_URI` and `MONGO_DATABASE`.
Restart with `python -m scripts.run_local` in a second terminal.

Verify the existing collection/teams and the 65 historical battles, finish a
new battle, and check that its reward reaches MySQL while its log reaches Atlas.
The VM must remain running whenever teammates use the shared MySQL database.
Schedule and test backups of both databases after the migration; VM disk storage
alone is not a backup.

## References

- [Google Cloud free-tier limits](https://docs.cloud.google.com/free/docs/free-cloud-features)
- [Create a Linux VM](https://docs.cloud.google.com/compute/docs/create-linux-vm-instance)
- [Find the project ID](https://docs.cloud.google.com/resource-manager/docs/view-update-projects)
- [External IP pricing](https://cloud.google.com/vpc/network-pricing)
- [MySQL APT installation](https://dev.mysql.com/doc/refman/8.4/en/linux-installation-apt-repo.html)
- [MySQL logical backups](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html)
- [SSH port forwarding](https://docs.cloud.google.com/solutions/connecting-securely)
