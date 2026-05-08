"""
Seed extraction schemas from config/schemas/*.py into the database.

Each module must expose a module-level `SCHEMA: SchemaConfig` instance.
The seed script imports every module in that package and pushes its schema.

Run with: python config/seed_schemas.py [--force]

  --force   Update existing schemas instead of skipping them.
"""
import asyncio
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import AsyncSessionLocal
from db.repository import SchemaRepository
from models.schemas import SchemaConfig

_SCHEMAS_PKG = "config.schemas"
_SCHEMAS_DIR = Path(__file__).parent / "schemas"


def _load_schemas() -> list[SchemaConfig]:
    schemas: list[SchemaConfig] = []
    for path in sorted(_SCHEMAS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = importlib.import_module(f"{_SCHEMAS_PKG}.{path.stem}")
        schema = getattr(module, "SCHEMA", None)
        if schema is None:
            print(f"  warning  {path.name} has no SCHEMA — skipping")
            continue
        if not isinstance(schema, SchemaConfig):
            raise TypeError(f"{path.name}: SCHEMA must be SchemaConfig, got {type(schema)}")
        schemas.append(schema)
    return schemas


async def seed(force: bool = False) -> None:
    schemas = _load_schemas()
    if not schemas:
        print(f"No schema modules found in {_SCHEMAS_DIR}")
        return

    async with AsyncSessionLocal() as session:
        repo = SchemaRepository(session)
        for schema in schemas:
            existing = await repo.get_by_key(schema.key)
            if existing:
                if force:
                    data = schema.model_dump(mode="json")
                    for field, value in data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    await session.commit()
                    print(f"  updated  {schema.key}")
                else:
                    print(f"  skip     {schema.key} (already exists — use --force to update)")
            else:
                await repo.create(schema.model_dump(mode="json"))
                print(f"  created  {schema.key}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    print(f"Seeding schemas from {_SCHEMAS_PKG} ...")
    asyncio.run(seed(force=force))
    print("Done.")
