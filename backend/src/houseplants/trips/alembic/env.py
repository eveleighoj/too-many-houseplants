from alembic import context

from houseplants.common.migrations import run_chain_migrations
from houseplants.trips.models import SCHEMA, Base

run_chain_migrations(context, SCHEMA, Base.metadata)
