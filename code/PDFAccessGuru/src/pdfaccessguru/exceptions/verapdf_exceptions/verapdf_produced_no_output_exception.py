


class VeraPDFProducedNoOutputException(Exception):
    def __init__(self):
        super().__init__("Something went wrong while running VeraPdf because VeraPdf produced no output.")