import logging


class MyLogger:
    _logger: logging = None

    def __new__(cls, *args, **kwargs) -> logging:
        if cls._logger is None:
            cls._logger = super().__new__(cls, *args, **kwargs)
            cls._logger = logging.getLogger("aioclock")
            cls._logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s","event":"%(event)s","level_name":"%(level_name)s","method_name":"%(method_name)s","request":"","payload": "%(message)s"}'
            )
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)
            cls._logger.addHandler(streamHandler)

        return cls

    @classmethod
    def info(cls, message: str, event: str = None, method_name: str = None):
        cls._logger.info(
            message,
            extra={
                "event": f"{event}",
                "method_name": f"{method_name}",
            },
        )

    @classmethod
    def warn(cls, message: str, event: str = None, method_name: str = None):
        cls._logger.warn(
            message,
            extra={
                "event": f"{event}",
                "method_name": f"{method_name}",
            },
        )

    @classmethod
    def error(cls, message: str, event: str = None, method_name: str = None):
        cls._logger.error(
            message,
            extra={
                "event": f"{event}",
                "method_name": f"{method_name}",
            },
        )

    @classmethod
    def debug(cls, message: str, event: str = None, method_name: str = None):
        cls._logger.debug(
            message,
            extra={
                "event": f"{event}",
                "method_name": f"{method_name}",
            },
        )
