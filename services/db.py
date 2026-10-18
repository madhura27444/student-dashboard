import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from config import Config

def get_connection():
    """
    Returns a database connection based on Config.DB_TYPE.
    Defaults to SQLite if DB_TYPE is 'sqlite' or MySQL connection parameters are missing.
    """
    if Config.DB_TYPE.lower() == 'mysql':
        ssl_config = None
        if Config.DB_SSL_CA:
            if os.path.exists(Config.DB_SSL_CA):
                ssl_config = {'ca': Config.DB_SSL_CA}
            else:
                ssl_config = {'ssl_mode': 'REQUIRED'}
        
        return pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False,
            ssl=ssl_config
        )
    else:
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def _format_sql_for_engine(sql: str, db_type: str) -> str:
    """
    Standardizes parameterized SQL queries:
    Translates '%s' to '?' if running on SQLite,
    or translates '?' to '%s' if running on MySQL.
    """
    if db_type.lower() == 'sqlite':
        # Replace %s with ? only if %s is used as placeholder
        # Simple token replacement that preserves %% if any
        return sql.replace('%s', '?')
    else:
        return sql.replace('?', '%s')

def query_all(sql: str, params: tuple = ()) -> list:
    """
    Executes a SELECT query and returns all matching rows as dictionaries.
    """
    db_type = Config.DB_TYPE.lower()
    formatted_sql = _format_sql_for_engine(sql, db_type)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(formatted_sql, params)
        if db_type == 'sqlite':
            rows = [dict(row) for row in cur.fetchall()]
        else:
            rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()

def query_one(sql: str, params: tuple = ()) -> dict:
    """
    Executes a SELECT query and returns a single row as a dictionary, or None.
    """
    db_type = Config.DB_TYPE.lower()
    formatted_sql = _format_sql_for_engine(sql, db_type)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(formatted_sql, params)
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        return dict(row) if db_type == 'sqlite' else row
    finally:
        conn.close()

def execute(sql: str, params: tuple = ()) -> int:
    """
    Executes an INSERT, UPDATE, or DELETE query and commits the transaction.
    Returns the lastrowid for INSERT, or rowcount.
    """
    db_type = Config.DB_TYPE.lower()
    formatted_sql = _format_sql_for_engine(sql, db_type)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(formatted_sql, params)
        conn.commit()
        last_id = cur.lastrowid
        row_count = cur.rowcount
        cur.close()
        return last_id if last_id else row_count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_transaction(operations: list) -> bool:
    """
    Executes multiple SQL operations inside an atomic transaction.
    Each item in operations is a tuple: (sql_statement, params_tuple)
    """
    db_type = Config.DB_TYPE.lower()
    conn = get_connection()
    try:
        cur = conn.cursor()
        for sql, params in operations:
            fmt_sql = _format_sql_for_engine(sql, db_type)
            cur.execute(fmt_sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db(seed_if_empty: bool = True):
    """
    Initializes database schema and optionally seeds realistic demo data if no students exist.
    """
    db_type = Config.DB_TYPE.lower()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_file = 'schema_mysql.sql' if db_type == 'mysql' else 'schema.sql'
    schema_path = os.path.join(base_dir, schema_file)
    seed_path = os.path.join(base_dir, 'seed.sql')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        cur = conn.cursor()
        if db_type == 'sqlite':
            conn.executescript(schema_sql)
            conn.commit()
        else:
            # MySQL split statements
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for stmt in statements:
                cur.execute(stmt)
            conn.commit()

        # Check if students table is empty
        cur.execute("SELECT COUNT(*) AS cnt FROM students")
        res = cur.fetchone()
        cnt = res['cnt'] if isinstance(res, dict) else res[0]

        if cnt == 0 and seed_if_empty and os.path.exists(seed_path):
            with open(seed_path, 'r', encoding='utf-8') as f:
                seed_sql = f.read()
            if db_type == 'sqlite':
                conn.executescript(seed_sql)
                conn.commit()
            else:
                seed_statements = [s.strip() for s in seed_sql.split(';') if s.strip()]
                for s_stmt in seed_statements:
                    cur.execute(s_stmt)
                conn.commit()
        cur.close()
    finally:
        conn.close()
