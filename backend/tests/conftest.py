import os
import pytest

# Ensure pytest runs against the deterministic InMemoryStore with demo auth enabled
os.environ["USE_FIRESTORE"] = "false"
os.environ["ENABLE_DEMO_AUTH"] = "true"
os.environ["ENVIRONMENT"] = "development"

from app.config import settings
settings.use_firestore = False
settings.enable_demo_auth = True
settings.environment = "development"

from app.db import InMemoryStore
import app.db as db_module
import app.routes.guidelines_routes as gr
import app.routes.drafts_routes as dr
import app.routes.auth_routes as ar
import app.routes.audit_routes as aur
import app.auth as auth_mod
import app.checker as chk

@pytest.fixture(autouse=True)
def reset_in_memory_db():
    """Reset InMemoryStore for every test to ensure complete test isolation."""
    fresh_db = InMemoryStore()
    db_module.db = fresh_db
    gr.db = fresh_db
    dr.db = fresh_db
    ar.db = fresh_db
    aur.db = fresh_db
    auth_mod.db = fresh_db
    chk.db = fresh_db
    yield
