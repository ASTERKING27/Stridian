"""
Bring an existing database up to date with the models.

SQLAlchemy's `create_all` only creates tables that are missing entirely — it will not
touch a table that already exists, so every time a column is added to models.py an older
database keeps working right up until something writes the new field, then fails with
"table students has no column named ...". That surfaces as a 500 on a form submit, which
is a miserable way to find out.

This walks the model metadata against what is actually on disk and issues the ALTER
TABLE statements needed, on every startup. It only ever adds columns: nothing is dropped,
renamed or retyped, so running it against an up-to-date database does nothing at all.

Why not Alembic: this app is one SQLite file and the only migration it has ever needed is
"add a nullable column". Alembic is a revision graph, a config file and a migrations
directory to solve a problem that is twenty lines of introspection here. If the schema
ever needs a real rename or a data backfill, that is the point to bring Alembic in.
"""

from sqlalchemy import inspect, text


def _literal(value):
    """Render a Python default as a SQL literal for the DEFAULT clause."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"   # Postgres refuses 1/0 for a BOOLEAN
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _scalar_default(column):
    """The column's default, if it is a plain value rather than a callable."""
    default = column.default
    if default is None or not getattr(default, "is_scalar", False):
        return None
    return default.arg


def ensure_columns(engine, metadata):
    """Add any column the models declare that the database is missing.

    Returns (added, skipped) — `added` as "table.column" strings, `skipped` as
    (table.column, reason) for anything that cannot be added in place.
    """
    inspector = inspect(engine)
    added, skipped = [], []

    # each ALTER runs in its own transaction: on Postgres one failure would otherwise
    # abort — and roll back — every column added before it
    for table in metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # create_all will build it from scratch

        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue

            where = f"{table.name}.{column.name}"
            ddl_type = column.type.compile(engine.dialect)
            default = _scalar_default(column)

            # SQLite cannot add a NOT NULL column to a populated table unless the
            # statement carries a default for the rows already there.
            if not column.nullable and default is None:
                skipped.append((where, "NOT NULL with no default — add it by hand"))
                continue
            if getattr(column, "unique", False):
                skipped.append((where, "UNIQUE cannot be added in place"))
                continue

            clause = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'
            if not column.nullable:
                clause += " NOT NULL"
            if default is not None:
                clause += f" DEFAULT {_literal(default)}"

            try:
                with engine.begin() as conn:
                    conn.execute(text(clause))
                added.append(where)
            except Exception as exc:  # noqa: BLE001 - report, never abort startup
                skipped.append((where, str(exc).split("\n")[0]))

    return added, skipped


def run(engine, metadata, announce=print):
    """Migrate and say what happened, so a surprise is visible in the server log."""
    added, skipped = ensure_columns(engine, metadata)
    if added:
        announce(f"[schema] added {len(added)} missing column(s): {', '.join(added)}")
    for where, reason in skipped:
        announce(f"[schema] could not add {where}: {reason}")
    return added, skipped
