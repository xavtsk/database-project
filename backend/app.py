"""Local browser application. Start with python3 -m backend.app."""
import os
import secrets

from flask import Flask, jsonify, render_template, request, session
from pymongo.errors import PyMongoError
import pymysql

from backend.config import ROOT
from backend.db import mongo_client, mongo_database, query
from backend.errors import ValidationError, integer
from backend.catalog import catalog
from backend.pokedex import service as pokedex
from backend.teams import service as teams
from backend.team_analysis.service import analyse
from backend.battles import service as battles
from backend.analytics import service as analytics


def create_app(test_config=None):
    app = Flask(__name__, template_folder=str(ROOT / "frontend"), static_folder=str(ROOT / "frontend/static"))
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        directory = ROOT / ".local"
        directory.mkdir(exist_ok=True)
        path = directory / "session-secret"
        if not path.exists():
            path.write_text(secrets.token_hex(32))
            path.chmod(0o600)
        secret = path.read_text().strip()
    app.config.update(SECRET_KEY=secret, MAX_CONTENT_LENGTH=32768, SESSION_COOKIE_SAMESITE="Strict", SESSION_COOKIE_HTTPONLY=True)
    if test_config:
        app.config.update(test_config)
    client = mongo_client()
    logs = mongo_database(client).battles
    app.extensions["mongo"] = client
    app.extensions["battles"] = logs

    def selected():
        trainer_id = session.get("trainer_id")
        if trainer_id is None:
            raise ValidationError("Choose or create a trainer profile first")
        teams.trainer(trainer_id)
        return trainer_id

    def payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("A JSON object is required")
        return data

    @app.before_request
    def protect_actions():
        if request.method in ("POST", "PUT", "DELETE"):
            expected = session.get("csrf")
            if not expected or not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), expected):
                return jsonify(error="Session expired; refresh the page before trying again"), 403

    @app.errorhandler(ValidationError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(PyMongoError)
    @app.errorhandler(pymysql.MySQLError)
    def unavailable(error):
        app.logger.exception("Database operation failed")
        return jsonify(error="Database unavailable. Check the local services and configuration, then retry. Saved battle rewards can be recovered from history."), 503

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/session")
    def current_session():
        session.setdefault("csrf", secrets.token_hex(24))
        profile = teams.trainer(session["trainer_id"]) if session.get("trainer_id") else None
        return jsonify(csrf=session["csrf"], trainer=profile, profiles=teams.profiles())

    @app.post("/api/profiles")
    def new_profile():
        session["trainer_id"] = teams.create_profile(payload().get("name"))
        return jsonify(trainer=teams.trainer(session["trainer_id"])), 201

    @app.post("/api/profiles/select")
    def select_profile():
        profile = teams.trainer(integer(payload().get("id"), "Trainer ID"))
        session["trainer_id"] = profile["id"]
        return jsonify(trainer=profile)

    @app.post("/api/starter")
    def starter():
        return jsonify(team_id=teams.choose_starter(selected(), payload().get("pokemon_id")))

    @app.get("/api/pokemon")
    def browse():
        return jsonify(pokemon=pokedex.browse(request.args.get("q", "")[:80], request.args.get("type", "")[:20]), types=catalog()[1])

    @app.get("/api/pokemon/<int:pokemon_id>")
    def pokemon_detail(pokemon_id):
        return jsonify(pokedex.detail(pokemon_id))

    @app.get("/api/collection")
    def collection():
        return jsonify(pokemon=teams.collection(selected()))

    @app.get("/api/teams")
    def team_list():
        return jsonify(teams=teams.list_teams(selected()))

    @app.post("/api/teams")
    def team_create():
        data = payload()
        return jsonify(id=teams.save_team(selected(), data.get("name"), data.get("members"))), 201

    @app.get("/api/teams/<int:team_id>")
    def team_detail(team_id):
        return jsonify(teams.get_team(selected(), team_id))

    @app.put("/api/teams/<int:team_id>")
    def team_update(team_id):
        data = payload()
        return jsonify(id=teams.save_team(selected(), data.get("name"), data.get("members"), team_id))

    @app.delete("/api/teams/<int:team_id>")
    def team_delete(team_id):
        teams.delete_team(selected(), team_id)
        return jsonify(ok=True)

    @app.get("/api/teams/<int:team_id>/analysis")
    def analysis(team_id):
        return jsonify(analyse(selected(), team_id))

    @app.get("/api/battles")
    def battle_history():
        return jsonify(battles=analytics.history(logs, selected()))

    @app.post("/api/battles")
    def battle_start():
        data = payload()
        return jsonify(battles.start_battle(logs, selected(), data.get("team_id"), data.get("difficulty"))), 201

    @app.get("/api/battles/<battle_id>")
    def battle_detail(battle_id):
        return jsonify(battles.get_battle(logs, selected(), battle_id))

    @app.post("/api/battles/<battle_id>/actions")
    def battle_action(battle_id):
        data = payload()
        return jsonify(battles.act(logs, selected(), battle_id, data.get("revision"), data.get("action")))

    @app.get("/api/analytics")
    def battle_analytics():
        return jsonify(analytics.analytics(logs, selected()))

    @app.get("/api/health")
    def health():
        query("SELECT 1")
        client.admin.command("ping")
        return jsonify(sql="ready", mongodb="ready")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
