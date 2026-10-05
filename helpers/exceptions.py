"""
Custom exceptions used by the Smart Fitness Session Analyzer.
"""


class InvalidIdentifierError(ValueError):
    """Raised when an identifier has an invalid format."""

    def __init__(self, field, reason):
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


class InvalidRecordError(ValueError):
    """Raised when a CSV record cannot be accepted."""

    def __init__(self, field, reason):
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


class DataFileError(Exception):
    """Raised when a whole file cannot be read or written (missing, unreadable, bad header)."""

    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")