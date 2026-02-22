"""RQ Worker entrypoint.

Run with: python -m app.worker
"""

from redis import Redis
from rq import Worker, Queue

from app.config import settings


def main() -> None:
    """Start the RQ worker listening on the default queue."""
    redis_conn = Redis.from_url(settings.redis_url)
    queues = [Queue(connection=redis_conn)]

    print(f"Starting RQ worker, listening on queue 'default'...")
    print(f"Redis URL: {settings.redis_url}")

    worker = Worker(queues, connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
