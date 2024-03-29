import os
import sqlite3
import tomllib

import argon2.low_level
from flask import abort, g, redirect, request, url_for, Flask, render_template

from . import nvi

app = Flask(__name__)
with open(os.environ.get("CONFIG_PATH", "config.toml"), "rb") as f:
    app.config.update(tomllib.load(f))

# We will access sqlite from a multithreaded context, so we need to ensure that the
# sqlite3 library's thread safety option allows it. This also forces us to not use
# a forking WSGI server like Gunicorn since the multithreaded assumption will break
# in a non-nice way.
assert sqlite3.threadsafety == 3
db = sqlite3.connect(app.config["database_path"], check_same_thread=False)
with db:
    db.execute("""
CREATE TABLE IF NOT EXISTS voters (
    hashed_tckn BLOB PRIMARY KEY
) STRICT;
""")
    db.execute("""
CREATE TABLE IF NOT EXISTS votes (
    votee_index INTEGER PRIMARY KEY,
    vote_amount INTEGER NOT NULL
) STRICT;
""")
    for votee_index in range(len(app.config["candidates"])):
        db.execute("INSERT OR IGNORE INTO votes(votee_index, vote_amount) VALUES(?, 0);", (votee_index,))

# DO NOT TOUCH THIS FUNCTION IF YOU DO NOT KNOW WHAT YOU ARE DOING.
# Populated with the recommended parameters from 2023-03-12. Changing parameters will break the whole DB as the
# hashes are used as ids. This function needs to be deterministic, so field based salts will not work.
ARGON2_VERSION: int = 19
ARGON2_TYPE: argon2.low_level.Type = argon2.low_level.Type.ID
ARGON2_TIME_COST: int = 3
ARGON2_MEMORY_COST: int = 65536
ARGON2_PARALLELISM: int = 4
ARGON2_HASH_LEN: int = 32
SALT: bytes = app.config["tckn_salt"].encode()
def hash_tckn(tckn: str) -> bytes:
    return argon2.low_level.hash_secret_raw(secret=tckn.encode(), salt=SALT, time_cost=ARGON2_TIME_COST, memory_cost=ARGON2_MEMORY_COST,
                                            parallelism=ARGON2_PARALLELISM, hash_len=ARGON2_HASH_LEN, type=ARGON2_TYPE, version=ARGON2_VERSION)


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "GET":
        cur = db.cursor()
        cur.execute("SELECT votee_index, vote_amount FROM votes;")

        vote_counts: dict[str, int] = dict(map(lambda p: (app.config["candidates"][p[0]], p[1]), cur.fetchall()))
        total_votes = sum(vote_counts.values())
        if not total_votes:
            vote_rates = {candidate: 0 for candidate in vote_counts}
        else:
            vote_rates = {candidate: round((100 * vote_counts[candidate]) / total_votes, 2) for candidate in vote_counts}
        return render_template("index.html", vote_counts=vote_counts, total_votes=total_votes, vote_rates=vote_rates, candidates=app.config["candidates"])
    elif request.method == "POST":
        # FIXME: Add captcha.
        try:
            vote: int = int(request.form["vote"])
        except (KeyError, ValueError):
            abort(400)

        if vote >= len(app.config["candidates"]):
            abort(400)

        # FIXME: Character check?
        try:
            name: str = request.form["name"]
            surname: str = request.form["surname"]
        except KeyError:
            abort(400)

        if len(name) > 32 or len(surname) > 32:
            abort(400)

        try:
            birth_year: int = int(request.form["birth_year"])
        except (KeyError, ValueError):
            abort(400)

        # FIXME: High bound does not have enough information?
        if birth_year < 1900 or birth_year > 2003:
            abort(400)

        try:
            tckn: str = request.form["tckn"]
        except (KeyError, ValueError):
            abort(400)

        if not nvi.validate_tckn(tckn):
            abort(400)

        hashed_tckn = hash_tckn(tckn)
        cur = db.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM voters WHERE hashed_tckn = ? LIMIT 1);", (hashed_tckn,))

        if cur.fetchone()[0]:
            abort(409)

        if not nvi.verify_tckn(tckn, name=name, surname=surname, birth_year=request.form["birth_year"]):
            abort(401)

        with db:
            cur = db.cursor()
            cur.execute("INSERT INTO voters(hashed_tckn) VALUES(?);", (hashed_tckn,))
            cur.execute("UPDATE votes SET vote_amount = vote_amount + 1 WHERE votee_index = ?;", (vote,))

        return render_template("success.html")


@app.errorhandler(400)
@app.errorhandler(401)
def invalid_data(error: int):
    return render_template("error.html", err_message="Girdiğiniz bilgilerde bir hata tespit edilmiştir. Lütfen kontrol edip tekrar deneyiniz.")


@app.errorhandler(409)
def conflicted_request(error: int):
    return render_template("error.html", err_message="Daha önce oy kullandığınız için tekrardan oy kullanamazsınız. Detaylı bilgi için Sıkça "
                                                     "Sorulan Soruları okuyunuz.")
