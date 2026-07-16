import uuid

# Fixed, deterministic IDs for the single seeded demo org/user (see
# app/db/seeds/seed_demo.py). Phase 2-3 routes resolve "current org/user"
# to these constants via app.core.deps; Phase 4 replaces that dependency
# with identity derived from a validated JWT, at which point these
# constants stop being read outside of the seed script itself.
DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
