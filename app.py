from flask import Flask, send_from_directory

from db import initialize_database
from routes.auth import auth_bp, delete_account as delete_account_handler
from routes.wallet import wallet_bp
from routes.transactions import transactions_bp


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = "upi-fraud-sim-secret-key"

    initialize_database()

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(wallet_bp, url_prefix="/api")
    app.register_blueprint(transactions_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return send_from_directory("templates", "index.html")

    @app.delete("/delete_account")
    @app.delete("/api/delete_account")
    def delete_account_alias():
        return delete_account_handler()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
