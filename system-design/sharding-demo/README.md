# Sharding demo — 1 logical DB → 3 physical shards

A live, hands-on demo: take a `users` + `orders` schema and spread the rows
across **3 separate Postgres instances**. All routing logic is ~40 lines of
Python. Nothing in Postgres knows sharding exists.

```
            ┌─────────────┐
   app  ──▶ │  shard.py   │   shard_of(user_id) = md5(user_id) % 3
            └──┬───┬───┬──┘
        shard0 │   │   │ shard2
          shard1   (Postgres :5433 / :5434 / :5435)
```

## Setup (do before class)

```bash
cd sharding-demo
docker compose up -d       # pulls postgres:16 the first time
./shard.py init            # apply schema.sql to all 3 shards
./shard.py seed 30         # 30 users + random orders, routed by hash
```

Teardown: `docker compose down -v`

## Run sheet (~20–25 min)

**1. The key idea (2 min)**
One table too big for one box. Split by a *shard key* (`user_id`). Pick the
function: range, hash, or lookup. We use `md5(user_id) % 3`.

```bash
./shard.py where 7      # key 7  -> shard index 0 -> shard0
./shard.py where 8      # key 8  -> shard index 2 -> shard2
```

**2. Show the shards are just plain databases (2 min)**

```bash
docker compose exec shard0 psql -U demo -d appdb -c "\dt"
docker compose exec shard0 psql -U demo -d appdb -c "SELECT id,name FROM users LIMIT 5;"
docker compose exec shard1 psql -U demo -d appdb -c "SELECT id,name FROM users LIMIT 5;"
# different rows on each — disjoint sets, no overlap
```

**3. Distribution — did hashing balance it? (3 min)**

```bash
./shard.py distribution
```
Roughly even. Ask: what if we'd sharded by `city` instead? (hotspots — Mumbai
shard melts). Good shard key = high cardinality + even access.

**4. A single-key read hits ONE shard (3 min)**

```bash
./shard.py get-user 12
```
Point out: the router computed the shard, opened one connection. Orders are
co-located (sharded by the same `user_id`) so "user + their orders" never
crosses a shard. This is the whole payoff.

**5. A cross-shard query = scatter–gather (4 min)**

```bash
./shard.py query-all "SELECT count(*), sum(amount) FROM orders;"
./shard.py top-cities
```
No shard can answer "top cities globally" alone. App fans out, waits for the
slowest shard, merges partials. Discuss: `ORDER BY ... LIMIT`, `JOIN` across
users on different shards, `COUNT(DISTINCT)` — all get hard. This is why teams
denormalize or keep a separate analytics store.

**6. Add a user live (2 min)**

```bash
./shard.py add-user "Ada" Pune
./shard.py distribution
```

**7. Why scaling out hurts (4 min)**

```bash
./shard.py reshard 4     # ~70% of rows would move going 3 -> 4
```
`% 3` → `% 4` remaps almost everything. Fixes:
- **Consistent hashing** — only ~1/N keys move when adding a node.
- **Virtual buckets** — hash into e.g. 4096 buckets, map buckets→nodes; move
  buckets, not keys.

**8. Wrap (1 min)** — what the app gave up: cross-shard joins, global unique
constraints (we assign ids in the app), transactions across shards, easy
resharding. What it bought: horizontal write scale.

## Commands

| command | what it does |
|---|---|
| `./shard.py init` | apply `schema.sql` to every shard |
| `./shard.py seed N` | create N users + random orders |
| `./shard.py add-user NAME CITY` | insert one user |
| `./shard.py get-user ID` | user + orders (one shard) |
| `./shard.py where KEY` | print which shard a key maps to |
| `./shard.py distribution` | rows per shard |
| `./shard.py query-all "SQL"` | run SQL on all shards, print each |
| `./shard.py top-cities` | cross-shard aggregation merged in app |
| `./shard.py reshard M` | % of rows that move going 3 → M shards |

## Connect manually

| shard | host port |
|---|---|
| shard0 | `psql postgresql://demo:demo@localhost:5433/appdb` |
| shard1 | `psql postgresql://demo:demo@localhost:5434/appdb` |
| shard2 | `psql postgresql://demo:demo@localhost:5435/appdb` |
