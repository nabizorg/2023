import sqlite3

from flask import abort, g, request, Flask

app = Flask(__name__)
app.config["DATABASE_PATH"] = "votes.db"

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


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "GET":
        abort(501)
    elif request.method == "POST":
        abort(501)
