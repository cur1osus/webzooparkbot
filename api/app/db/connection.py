from __future__ import annotations

import os

import pymysql
import pymysql.cursors


DB_CFG = dict(
    host="127.0.0.1",
    user=os.getenv("DB_USER", "admin_zoopark"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "zoopark"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)


def get_db():
    return pymysql.connect(**DB_CFG)
