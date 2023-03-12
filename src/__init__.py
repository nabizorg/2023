import sqlite3

import argon2.low_level
from flask import abort, g, request, Flask

app = Flask(__name__)
app.config["DATABASE_PATH"] = "votes.db"
app.config["TCKN_SALT"] = "foobarbaz"

# We will access sqlite from a multithreaded context, so we need to ensure that the
# sqlite3 library's thread safety option allows it. This also forces us to not use
# a forking WSGI server like Gunicorn since the multithreaded assumption will break
# in a non-nice way.
assert sqlite3.threadsafety == 3
db = sqlite3.connect(app.config["DATABASE_PATH"], check_same_thread=False)
with db:
    db.execute("""
CREATE TABLE IF NOT EXISTS votes (
    hashed_tckn BLOB PRIMARY KEY,
    vote INTEGER NOT NULL
) STRICT;
""")

# DO NOT TOUCH THIS FUNCTION IF YOU DO NOT KNOW WHAT YOU ARE DOING.
# Populated with the recommended parameters from 2023-03-12. Changing parameters will break the whole DB as the
# hashes are used as ids. This function needs to be deterministic, so field based salts will not work.
ARGON2_VERSION: int = 19
ARGON2_TYPE: argon2.low_level.Type = argon2.low_level.Type.ID
ARGON2_TIME_COST: int = 3
ARGON2_MEMORY_COST: int = 65536
ARGON2_PARALLELISM: int = 4
ARGON2_HASH_LEN: int = 32
SALT: bytes = app.config["TCKN_SALT"].encode()
def hash_tckn(tckn: str) -> bytes:
    return argon2.low_level.hash_secret_raw(secret=tckn.encode(), salt=SALT, time_cost=ARGON2_TIME_COST, memory_cost=ARGON2_MEMORY_COST,
                                            parallelism=ARGON2_PARALLELISM, hash_len=ARGON2_HASH_LEN, type=ARGON2_TYPE, version=ARGON2_VERSION)


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "GET":
        abort(501)
    elif request.method == "POST":
        abort(501)
