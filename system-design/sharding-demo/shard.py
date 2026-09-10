#!/usr/bin/env python3
"""
Tiny sharding router for the class demo.

  3 shards  = 3 Postgres containers (see docker-compose.yml)
  shard_of(key) = md5(key) % 3     <-- the whole "sharding algorithm"

No Postgres driver needed: we shell out to `psql` inside each container via
`docker compose exec`. That keeps every SQL statement visible on screen.

Usage:
  ./shard.py init                       apply schema.sql to all shards
  ./shard.py seed 30                    create 30 users + random orders
  ./shard.py add-user "Neha" Pune       insert one user (id auto = max+1 globally)
  ./shard.py get-user 7                 fetch user 7 + orders  (hits ONE shard)
  ./shard.py where 7                    just print which shard key 7 lives on
  ./shard.py distribution               count rows per shard
  ./shard.py query-all "SELECT ..."     scatter-gather: run SQL on every shard
  ./shard.py top-cities                 cross-shard aggregation done in the app
  ./shard.py reshard 4                  show why hash-mod resharding hurts
"""
import hashlib
import subprocess
import sys

SHARDS = ["shard0", "shard1", "shard2"]


def shard_index(key: int, n: int = len(SHARDS)) -> int:
    h = hashlib.md5(str(key).encode()).hexdigest()
    return int(h, 16) % n


def shard_for(key: int) -> str:
    return SHARDS[shard_index(key)]


def psql(service: str, sql: str, quiet: bool = False) -> str:
    if not quiet:
        print(f"  \033[90m[{service}] {sql.strip()}\033[0m")
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", service,
         "psql", "-U", "demo", "-d", "appdb", "-v", "ON_ERROR_STOP=1",
         "-t", "-A", "-F", " | ", "-c", sql],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"ERROR on {service}: {out.stderr.strip()}")
    return out.stdout.strip()


def all_shards(sql: str):
    return {s: psql(s, sql) for s in SHARDS}


# ---------- commands ----------

def cmd_init():
    schema = open("schema.sql").read()
    for s in SHARDS:
        psql(s, schema, quiet=True)
        print(f"  {s}: schema applied")


def _next_id(table: str) -> int:
    mx = 0
    for s in SHARDS:
        v = psql(s, f"SELECT COALESCE(MAX(id),0) FROM {table};", quiet=True)
        mx = max(mx, int(v or 0))
    return mx + 1


def cmd_add_user(name: str, city: str) -> int:
    uid = _next_id("users")
    target = shard_for(uid)
    print(f"user id {uid} -> md5({uid}) % 3 = {shard_index(uid)} -> {target}")
    psql(target, f"INSERT INTO users(id,name,city) VALUES ({uid},'{name}','{city}');")
    return uid


def cmd_seed(count: int):
    import random
    cities = ["Pune", "Bengaluru", "Delhi", "Mumbai", "Hyderabad", "Chennai"]
    names = ["Neha", "Rahul", "Simran", "Arjun", "Priya", "Vikram", "Anita", "Karan"]
    oid = _next_id("orders")
    for i in range(count):
        uid = cmd_add_user(f"{random.choice(names)}{i}", random.choice(cities))
        for _ in range(random.randint(0, 3)):
            amt = round(random.uniform(100, 5000), 2)
            psql(shard_for(uid),
                 f"INSERT INTO orders(id,user_id,amount) VALUES ({oid},{uid},{amt});",
                 quiet=True)
            oid += 1
    print(f"\nseeded {count} users.")
    cmd_distribution()


def cmd_get_user(uid: int):
    target = shard_for(uid)
    print(f"routing: user {uid} -> {target}  (1 shard queried, not {len(SHARDS)})\n")
    print(psql(target, f"SELECT id,name,city FROM users WHERE id={uid};"))
    print("orders:")
    print(psql(target, f"SELECT id,amount FROM orders WHERE user_id={uid} ORDER BY id;"))


def cmd_where(key: int):
    print(f"key {key} -> shard index {shard_index(key)} -> {shard_for(key)}")


def cmd_distribution():
    print("\nrows per shard:")
    total_u = total_o = 0
    for s in SHARDS:
        u = int(psql(s, "SELECT count(*) FROM users;", quiet=True))
        o = int(psql(s, "SELECT count(*) FROM orders;", quiet=True))
        total_u += u
        total_o += o
        bar = "#" * u
        print(f"  {s}: {u:3d} users  {o:3d} orders  {bar}")
    print(f"  total: {total_u} users, {total_o} orders")


def cmd_query_all(sql: str):
    print("scatter-gather: same query on every shard\n")
    for s, rows in all_shards(sql).items():
        print(f"--- {s} ---")
        print(rows or "(no rows)")


def cmd_top_cities():
    """Aggregation that no single shard can answer — the app merges partials."""
    from collections import Counter
    merged = Counter()
    for s in SHARDS:
        rows = psql(s, "SELECT city, count(*) FROM users GROUP BY city;", quiet=True)
        for line in filter(None, rows.splitlines()):
            city, n = line.split(" | ")
            merged[city] += int(n)
    print("global city counts (merged in app from 3 partial results):")
    for city, n in merged.most_common():
        print(f"  {city:12s} {n}")


def cmd_reshard(new_n: int):
    """How many existing users would move if we go from 3 -> new_n shards?"""
    moved = kept = 0
    for s in SHARDS:
        ids = psql(s, "SELECT id FROM users;", quiet=True).split()
        for raw in ids:
            uid = int(raw)
            if shard_index(uid, new_n) == shard_index(uid, len(SHARDS)):
                kept += 1
            else:
                moved += 1
    total = moved + kept
    pct = (100 * moved / total) if total else 0
    print(f"resharding 3 -> {new_n}: {moved}/{total} users change shard ({pct:.0f}%)")
    print("this is why naive hash-mod sharding is painful to scale")
    print("(fixes: consistent hashing, or many virtual buckets mapped to nodes)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, *args = sys.argv[1:]
    dispatch = {
        "init": cmd_init,
        "seed": lambda: cmd_seed(int(args[0])),
        "add-user": lambda: cmd_add_user(args[0], args[1]),
        "get-user": lambda: cmd_get_user(int(args[0])),
        "where": lambda: cmd_where(int(args[0])),
        "distribution": cmd_distribution,
        "query-all": lambda: cmd_query_all(args[0]),
        "top-cities": cmd_top_cities,
        "reshard": lambda: cmd_reshard(int(args[0])),
    }
    if cmd not in dispatch:
        print(__doc__)
        sys.exit(f"unknown command: {cmd}")
    dispatch[cmd]()


if __name__ == "__main__":
    main()
