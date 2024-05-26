import logging
import subprocess
import sys

from aioclock import __version__

logger = logging.getLogger(__name__)


def run_command(command: str) -> None:
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError:
        logger.exception("Error executing command")
        sys.exit(1)


if __name__ == "__main__":
    command = "mike set-default latest"
    run_command(command)

    command = f"mike deploy --push --update-aliases {__version__} latest"
    run_command(command)
