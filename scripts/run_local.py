"""Load local .env settings and start the browser app. No virtual environment needed."""
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONNECTION_KEYS = {"SQL_HOST", "SQL_PORT", "SQL_USER", "SQL_PASSWORD", "SQL_DATABASE",
                   "SQL_SOCKET", "MONGO_URI", "MONGO_DATABASE"}


def load_environment():
    overrides = []
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key.strip().isidentifier():
                raise ValueError("Use KEY=value assignments in .env")
            values = shlex.split(value, comments=True)
            if len(values) > 1:
                raise ValueError(f"Quote values with spaces in .env: {key.strip()}")
            name, value = key.strip(), values[0] if values else ""
            if name in CONNECTION_KEYS and name in os.environ and os.environ[name] != value:
                if name not in overrides:
                    overrides.append(name)
            os.environ.setdefault(name, value)
    return overrides


def startup_failure(error, service):
    """Describe connection failures without echoing driver messages or credentials."""
    import pymysql
    from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure, PyMongoError
    if isinstance(error, pymysql.MySQLError):
        code = error.args[0] if error.args and isinstance(error.args[0], int) else None
        if code in (1044, 1045):
            return "MySQL rejected the project account. Check SQL_USER, SQL_PASSWORD and database permissions."
        if code in (1049, 1146):
            return "MySQL database or Pokemon catalogue is missing. Verify SQL_DATABASE selects the intended database before running setup."
        if os.getenv("SQL_HOST", "127.0.0.1") in ("127.0.0.1", "localhost") and os.getenv("SQL_PORT") == "3308":
            return ("MySQL connection through the SSH tunnel on local port 3308 failed. "
                    "Run .\\.local\\gcp\\start-tunnel.cmd in another terminal and keep it open; check the VM and its MySQL service are running.")
        return "MySQL connection failed. Check SQL_HOST, SQL_PORT and whether the configured server is running."
    if isinstance(error, PyMongoError):
        if isinstance(error, ConfigurationError):
            return "MongoDB connection settings are invalid. Check MONGO_URI in .env; keep the connection string private."
        if isinstance(error, OperationFailure):
            return "MongoDB rejected the database user or its permissions. Check MONGO_URI credentials and MONGO_DATABASE."
        if isinstance(error, ConnectionFailure):
            if os.getenv("MONGO_URI", "").startswith("mongodb+srv://"):
                return "MongoDB Atlas connection failed. Check internet access, cluster availability and the Atlas IP access list."
            return "MongoDB connection failed. Check MONGO_URI and whether the configured MongoDB server is running."
        return "MongoDB startup check failed. Check MONGO_URI and database access."
    return f"{service} startup failed ({type(error).__name__}). Check the project settings and installed dependencies."


def main():
    overrides = load_environment()
    if overrides:
        print("Terminal settings override .env for: " + ", ".join(overrides) +
              ". Clear these variables or use the private .local\\gcp\\run-cloud.cmd launcher for this computer.",
              file=sys.stderr)
    # Reuse an existing local MongoDB. The optional downloaded binary lives outside Git.
    binary = ROOT / ".local/mongodb/bin/mongod"
    if os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017") == "mongodb://127.0.0.1:27017" and binary.exists():
        try:
            with socket.create_connection(("127.0.0.1", 27017), timeout=1):
                pass
        except OSError:
            directory = ROOT / ".local/mongo-data"
            directory.mkdir(parents=True, exist_ok=True)
            subprocess.run([str(binary), "--dbpath", str(directory), "--logpath", str(ROOT / ".local/mongo.log"),
                            "--bind_ip", "127.0.0.1", "--port", "27017", "--fork"], check=True)
    from backend.app import create_app
    from backend.db import query
    service = "Application"
    try:
        app = create_app()
        service = "MySQL"
        query("SELECT id FROM pokemon LIMIT 1")
        service = "MongoDB"
        app.extensions["mongo"].admin.command("ping")
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    except Exception as error:
        raise SystemExit(startup_failure(error, service)) from None
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5050")), debug=False)


if __name__ == "__main__":
    main()
