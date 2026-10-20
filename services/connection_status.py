"""Log connection transitions without repeating every failed request."""
import logging
from threading import Lock


class ConnectionStatus:
    def __init__(self, name):
        self.name = name
        self._failed = False
        self._lock = Lock()

    def failed(self):
        with self._lock:
            if self._failed:
                return
            self._failed = True
            logging.error("СВЯЗЬ ПОТЕРЯНА: %s. Ожидаем успешного подключения.", self.name)

    def connected(self):
        with self._lock:
            if not self._failed:
                return
            self._failed = False
            logging.info("СВЯЗЬ ВОССТАНОВЛЕНА: %s.", self.name,
                         extra={"connection_restored": True})


database_connection = ConnectionStatus("PostgreSQL")
