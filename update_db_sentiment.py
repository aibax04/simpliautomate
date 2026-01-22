
import asyncio
from sqlalchemy import text
from backend.db.database import engine

async def add_sentiment_column():
    print("Adding sentiment_filter column to tracking_rules table...")
    try:
        async with engine.begin() as conn:
            # Check if column exists strictly to avoid error, or just try catch
            try:
                await conn.execute(text("ALTER TABLE tracking_rules ADD COLUMN sentiment_filter VARCHAR DEFAULT 'all'"))
                print("Column added successfully.")
            except Exception as e:
                if "duplicate column" in str(e) or "already exists" in str(e):
                    print("Column already exists.")
                else:
                    raise e
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(add_sentiment_column())
