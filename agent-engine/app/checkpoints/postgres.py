from app.config import settings

CHECKPOINT_CONFIG = {
    "connection_string": settings.CHECKPOINT_DB_URL,
    "schema_name": "langgraph",
}
