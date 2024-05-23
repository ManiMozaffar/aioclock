class BaseAioClockException(Exception):
    """Base exception for aioclock."""


class TaskIdNotFound(BaseAioClockException):
    """Task not found in the AioClock app."""
