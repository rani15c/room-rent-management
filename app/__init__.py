import os

from dotenv import load_dotenv
from flask import Flask

from .extensions import db

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///room_rent.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()
        _add_payment_gateway_columns()

    from .routes import main
    app.register_blueprint(main)
    return app


def _add_payment_gateway_columns():
    """Keep existing SQLite databases compatible with the payment gateway fields."""
    from sqlalchemy import inspect, text

    columns = {column["name"] for column in inspect(db.engine).get_columns("payment")}
    additions = {
        "gateway_order_id": "VARCHAR(100)",
        "gateway_payment_id": "VARCHAR(100)",
        "gateway_signature": "VARCHAR(255)",
    }
    with db.engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE payment ADD COLUMN {name} {column_type}"))
