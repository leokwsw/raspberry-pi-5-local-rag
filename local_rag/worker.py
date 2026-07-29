import signal
import time

from local_rag.config import Settings
from local_rag.database import Database
from local_rag.resources import JobQueue, ingestion_allowed, system_metrics


def main() -> None:
    settings = Settings()
    settings.ensure_directories()
    database, running = Database(settings.database_path), True
    database.migrate()
    queue = JobQueue(database)
    queue.recover()

    def stop(*_: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        if ingestion_allowed(system_metrics(str(settings.data_dir))):
            queue.claim()
        time.sleep(1)


if __name__ == "__main__":
    main()
