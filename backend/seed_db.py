import asyncio
from app.connectors.demo import DemoDataConnector
from app.db.database import create_tables

async def main():
    await create_tables()
    connector = DemoDataConnector()
    # import_data is async! Wait, in demo.py it was defined as async def import_data
    res = await connector.import_data()
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
