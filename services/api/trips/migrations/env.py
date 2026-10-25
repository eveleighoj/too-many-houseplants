from alembic import context

from api.common.migrations import run_chain_migrations
from api.trips.models import SCHEMA, Base

run_chain_migrations(context, SCHEMA, Base.metadata)
