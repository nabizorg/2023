#!/usr/bin/env python3

import random
import shutil
import sqlite3
import sys


def main():
    if len(sys.argv) != 2:
        print(f"USAGE: {sys.argv[0]} <sqlite database path> - Migrates a pre-pool database.")
        sys.exit(2)

    num = random.randint(3, 0x7FFFFFFF)
    print(f"Creating database backup with filename {sys.argv[1]}.prepool{num}")
    shutil.copy(sys.argv[1], f"{sys.argv[1]}.prepool{num}")

    db = sqlite3.connect(sys.argv[1])
    with db:
        db.execute("ALTER TABLE votes RENAME TO votes_old;")
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
        db.execute("INSERT INTO votes(votee_index, vote_amount) SELECT vote, COUNT(vote) FROM votes_old GROUP BY vote;")
        db.execute("INSERT INTO voters(hashed_tckn) SELECT hashed_tckn FROM votes_old;")
        db.execute("DROP TABLE votes_old;")
    print("Migration successful.")


if __name__ == "__main__":
    main()
