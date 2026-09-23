"""Load local .env settings and start the browser app. No virtual environment needed."""
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_environment():
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
            os.environ.setdefault(key.strip(), values[0] if values else "")


def main():
    load_environment()
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
    app = create_app()
    try:
        query("SELECT id FROM pokemon LIMIT 1")
        app.extensions["mongo"].admin.command("ping")
    except Exception:
        raise SystemExit("Databases are not ready. Follow README.md: configure .env, start MariaDB/MongoDB and run scripts.setup_databases.")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5050")), debug=False)


if __name__ == "__main__":
    main()
