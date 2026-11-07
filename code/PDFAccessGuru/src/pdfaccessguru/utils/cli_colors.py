

class CLIColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def blue(text: str) -> str:
        return f"{CLIColors.OKBLUE}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def cyan(text: str) -> str:
        return f"{CLIColors.OKCYAN}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def green(text: str) -> str:
        return f"{CLIColors.OKGREEN}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def color_warning(text: str) -> str:
        return f"{CLIColors.WARNING}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def color_fail(text: str) -> str:
        return f"{CLIColors.FAIL}{text}{CLIColors.ENDC}"    