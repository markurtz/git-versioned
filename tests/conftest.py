import logging
from collections.abc import Generator

import pytest
from loguru import logger


class PropagateHandler(logging.Handler):
    """
    Routes loguru logs to standard logging so that caplog can capture them.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Route loguru record to standard logging."""
        logging.getLogger(record.name).handle(record)


@pytest.fixture(autouse=True)
def caplog_loguru(
    caplog: pytest.LogCaptureFixture,
) -> Generator[pytest.LogCaptureFixture, None, None]:
    """
    Hook loguru into pytest's caplog fixture.

    This ensures that assertions like `assert "foo" in caplog.text` work
    seamlessly with Loguru output.
    """
    handler_id = logger.add(PropagateHandler(), format="{message}")
    yield caplog
    logger.remove(handler_id)
