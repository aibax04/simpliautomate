import asyncio
from sqlalchemy import text
from backend.db.database import engine, Base
from backend.db.models import Product, ProductCollateral

async def init_db():
    print("[DB] Initializing Product tables...")
    async with engine.begin() as conn:
        # We don't drop existing tables here to avoid data loss for existing users,
        # but since this is a new feature and I just changed Product schema,
        # I'll drop and recreate just these two.
        print("[DB] Dropping existing product tables if exists...")
        await conn.execute(text("DROP TABLE IF EXISTS product_collateral CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        
        print("[DB] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] Product tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
