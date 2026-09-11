import asyncio
from app.core.database import AsyncSessionLocal
from app.crud.complaint import list_complaints

async def main():
    async with AsyncSessionLocal() as db:
        items, total = await list_complaints(db)
        print(f"Total complaints: {total}")
        for c in items:
            print(f"ID={c.id} | No={c.complaint_number} | Batch={c.batch_number} | Product={c.product_name} | Thread={c.thread_id}")
            print(f"  Desc: {c.description}")

if __name__ == "__main__":
    asyncio.run(main())
