import asyncio, random
from contextlib import asynccontextmanager

class Throttler:
    def __init__(self, min_delay: int, max_delay: int):
        self.min = min_delay
        self.max = max_delay
    async def sleep(self):
        await asyncio.sleep(random.uniform(self.min, self.max))

@asynccontextmanager
async def limit_per_window(semaphore: asyncio.Semaphore):
    await semaphore.acquire()
    try:
        yield
    finally:
        semaphore.release()