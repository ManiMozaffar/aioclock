class BaseAioClockException(Exception):
    """Base exception for aioclock."""


class TaskIdNotFound(BaseAioClockException):
    """Task not found in the AioClock app."""


class TaskTimeoutError(BaseAioClockException, TimeoutError):
    """A task took longer than its timeout"""
