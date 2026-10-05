"""Custom exceptions for the fitness analyzer package.

Both exceptions carry an optional "field" attribute, so the code that
catches them (the loader) can log exactly which column caused the
problem, not just that "something" went wrong in the row.
"""

class InvalidIdentifierError(ValueError):
    """Raised when a participant or session identifier has an invalid format."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field

class InvalidRecordError(ValueError):
    """Raised when a CSV record cannot be accepted (missing field, bad
    type, impossible value, unknown participant, wrong row length, ...).
    """

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field