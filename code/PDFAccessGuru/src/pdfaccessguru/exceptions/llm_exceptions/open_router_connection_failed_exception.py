

class OpenRouterConnectionFailedException(Exception):
    """
    Exception raised when the connection to the OpenRouter API fails.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)