import json
import logging
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "service_discovery"

_BASE_ATTRS = frozenset(
    logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=None, exc_info=None
    ).__dict__
)


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


class _ExtrasFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _BASE_ATTRS and not key.startswith("_")
        }
        message = super().format(record)
        if not extras:
            return message
        rendered = ", ".join(f"{key}={value}" for key, value in extras.items())
        return f"{message} [{rendered}]"


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _BASE_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    logger = get_logger()
    logger.setLevel(level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_ExtrasFormatter("%(asctime)s | %(levelname)-8s | %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
