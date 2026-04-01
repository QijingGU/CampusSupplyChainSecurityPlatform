from sqlalchemy import inspect, text


SCHEMA_PATCHES: dict[str, dict[str, str]] = {
    "ids_events": {
        "event_origin": "VARCHAR(16)",
        "source_classification": "VARCHAR(32)",
        "detector_family": "VARCHAR(32)",
        "detector_name": "VARCHAR(64)",
        "source_rule_id": "VARCHAR(128)",
        "source_rule_name": "VARCHAR(128)",
        "source_version": "VARCHAR(64)",
        "source_freshness": "VARCHAR(16)",
        "event_fingerprint": "VARCHAR(255)",
        "correlation_key": "VARCHAR(255)",
        "ai_analysis": "TEXT",
        "ai_risk_level": "VARCHAR(32)",
        "ai_confidence": "INTEGER",
        "ai_analyzed_at": "DATETIME",
        "status": "VARCHAR(32)",
        "review_note": "TEXT",
        "action_taken": "VARCHAR(128)",
        "response_result": "VARCHAR(32)",
        "response_detail": "TEXT",
        "risk_score": "INTEGER",
        "confidence": "INTEGER",
        "hit_count": "INTEGER",
        "detect_detail": "TEXT",
    },
    "purchases": {
        "approved_by_id": "INTEGER",
        "rejected_reason": "TEXT",
        "destination": "VARCHAR(200)",
        "receiver_name": "VARCHAR(50)",
        "handoff_code": "VARCHAR(64)",
        "material_type": "VARCHAR(32)",
        "material_spec": "VARCHAR(128)",
        "estimated_amount": "FLOAT",
        "delivery_date": "DATETIME",
        "attachment_names": "VARCHAR(512)",
        "is_draft": "INTEGER",
        "urgent_level": "VARCHAR(16)",
        "approval_level": "VARCHAR(32)",
        "approval_required_role": "VARCHAR(32)",
        "approval_deadline_at": "DATETIME",
        "forwarded_to": "VARCHAR(64)",
        "forwarded_note": "VARCHAR(256)",
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
