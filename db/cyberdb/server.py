import os

import cyberdb

CYBER_DB_PATH = "./data.cdb"


def main():
    db = cyberdb.Server()
    if os.path.exists(CYBER_DB_PATH):
        db.load_db(CYBER_DB_PATH)
    db.set_backup(CYBER_DB_PATH, cycle=300)

    db.run(
        host="127.0.0.1",
        port=10000,
        password="1234567890",
        max_con=10000,
        encrypt=True,
        print_log=False
    )


if __name__ == "__main__":
    main()
