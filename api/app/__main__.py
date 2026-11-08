"""Container entry point with JSON logs from process startup."""
import uvicorn

from .config import get_settings
from .logjson import configure_logging


def main() -> None:
    configure_logging(get_settings().log_level)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_config=None,
                access_log=False, timeout_graceful_shutdown=180)


if __name__ == "__main__":
    main()
