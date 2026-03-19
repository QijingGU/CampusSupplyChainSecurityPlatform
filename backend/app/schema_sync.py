from sqlalchemy import inspect, text


SCHEMA_PATCHES: dict[str, dict[str, str]] = {
    "purchases": {
        "approved_by_id": "INTEGER",
        "rejected_reason": "TEXT",
        "destination": "VARCHAR(200)",
        "receiver_name": "VARCHAR(50)",
        "handoff_code": "VARCHAR(64)",
        "completed_at": "DATETIME",
    },
    "stock_ins": {
        "purchase_id": "INTEGER",
    },
    "stock_outs": {
        "purchase_id": "INTEGER",
        "destination": "VARCHAR(200)",
        "receiver_name": "VARCHAR(50)",
        "handoff_code": "VARCHAR(64)",
    },
    "deliveries": {
        "purchase_id": "INTEGER",
        "receiver_user_id": "INTEGER",
        "handoff_code": "VARCHAR(64)",
        "confirmed_by_id": "INTEGER",
        "confirmed_at": "DATETIME",
        "sign_remark": "TEXT",
    },
}


def ensure_schema(engine):
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in SCHEMA_PATCHES.items():
            existing = {col["name"] for col in inspector.get_columns(table)} if inspector.has_table(table) else set()
            for name, column_type in columns.items():
                if name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"))
