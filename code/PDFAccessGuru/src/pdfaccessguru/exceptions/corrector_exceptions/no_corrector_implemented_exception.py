

class NoCorrectorImplementedException(Exception):
    """
    Raised when no corrector function for the specified violation name is 
    neither defined nor implemented.
    """
    def __init__(self, violation_name: str):
        super().__init__(f"No corrector defined for violation with name '{violation_name}'")