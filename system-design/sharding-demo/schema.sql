-- This exact schema is applied to EVERY shard, unchanged.
-- Each shard holds a disjoint subset of users (and their orders).

CREATE TABLE IF NOT EXISTS users (
    id         BIGINT PRIMARY KEY,          -- global id, assigned by the app, not a serial
    name       TEXT        NOT NULL,
    city       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Orders are co-located with their user (sharded by the SAME key: user_id).
-- => "give me a user and all their orders" never crosses a shard.
CREATE TABLE IF NOT EXISTS orders (
    id       BIGINT PRIMARY KEY,
    user_id  BIGINT      NOT NULL REFERENCES users(id),
    amount   NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
