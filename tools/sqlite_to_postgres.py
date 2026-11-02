"""Перенос данных из файла SQLite в пустую базу Postgres. Исходный файл не меняется.

    DATABASE_URL=postgresql://... python tools/sqlite_to_postgres.py instance/caspianhub.db

Всё выполняется одной транзакцией: при ошибке в Postgres не останется ничего.
Если в целевой базе уже есть настройки сайта, скрипт откажется работать.
"""
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Setting  # noqa: E402


def self_reference_column(table):
    for fk in table.foreign_keys:
        if fk.column.table is table:
            return fk.parent
    return None


def main(source_path: str) -> int:
    if not Path(source_path).is_file():
        print(f"Файл не найден: {source_path}")
        return 1
    source = create_engine(f"sqlite:///{Path(source_path).resolve()}")
    existing = set(inspect(source).get_table_names())

    app = create_app("production")
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            print("DATABASE_URL должен указывать на Postgres.")
            return 1
        db.create_all()
        if Setting.query.count():
            print("В Postgres уже есть данные, перенос отменён: ничего не изменено.")
            return 1
        db.session.remove()

        total = 0
        with db.engine.begin() as target, source.connect() as reader:
            for table in db.metadata.sorted_tables:
                if table.name not in existing:
                    continue
                source_columns = {c["name"] for c in inspect(source).get_columns(table.name)}
                columns = [c for c in table.columns if c.name in source_columns]
                query = select(*columns)
                parent = self_reference_column(table)
                if parent is not None:      # сначала строки без родителя, иначе сработает внешний ключ
                    query = query.order_by(parent.is_not(None), parent, *table.primary_key.columns)
                rows = [dict(row._mapping) for row in reader.execute(query)]
                for row in rows:
                    target.execute(table.insert().values(**row))
                if "id" in table.columns and rows:
                    target.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', 'id'), "
                        f"(SELECT max(id) FROM \"{table.name}\"))"))
                check = target.execute(select(func.count()).select_from(table)).scalar()
                if check != len(rows):
                    raise RuntimeError(f"{table.name}: прочитано {len(rows)}, записано {check}")
                total += len(rows)
                print(f"  {table.name}: {len(rows)}")
        print(f"Перенесено строк: {total}.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
