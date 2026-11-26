"""
loguru.py — маленькая замена библиотеки loguru для хостинга без pip.
Поддерживает ровно то, что используют наши скрипты:
logger.remove(), logger.add(поток_или_файл, ...), logger.debug/info/warning/error(сообщение, *args, **kwargs).
Сообщения форматируются как в loguru: "текст {} и {имя}".format(...).
"""
import os
import sys
import threading
from datetime import datetime

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


class _Logger:
    def __init__(self):
        self._sinks = [(sys.stderr, None)]
        self._lock = threading.Lock()

    def remove(self, *_):
        self._sinks = []

    def add(self, sink, format=None, rotation=None, retention=None, level="DEBUG", **_):
        path = None
        if isinstance(sink, str):
            path = sink
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
        self._sinks.append((sink if path is None else None, path))
        return len(self._sinks)

    def _log(self, level, message, *args, **kwargs):
        try:
            text = str(message).format(*args, **kwargs) if (args or kwargs) else str(message)
        except Exception:
            text = " ".join([str(message)] + [str(a) for a in args])
        line = "{} | {} | {}\n".format(datetime.now().strftime("%H:%M:%S"), level, text)
        with self._lock:
            for stream, path in self._sinks:
                try:
                    if path:
                        if os.path.exists(path) and os.path.getsize(path) > 10 * 1024 * 1024:
                            os.replace(path, path + ".old")
                        with open(path, "a", encoding="utf-8") as f:
                            f.write(line)
                    else:
                        stream.write(line)
                        stream.flush()
                except Exception:
                    pass

    def debug(self, message, *args, **kwargs):
        self._log("DEBUG", message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._log("INFO", message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._log("WARNING", message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._log("ERROR", message, *args, **kwargs)


logger = _Logger()
