class ChiveInternalError(Exception):
    """Exception raised for internal errors in the Chive plugin."""

    def __init__(
        self,
        message: str,
    ):
        super().__init__(message)
        self.message = message

    def __str__(self):
        error_str = f"ChiveInternalError: {self.message}"
        return error_str
