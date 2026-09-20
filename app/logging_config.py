import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "method"):
            log_record["method"] = record.method

        if hasattr(record, "path"):
            log_record["path"] = record.path

        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code

        return json.dumps(log_record)


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.handlers.clear()
    logger.addHandler(handler)