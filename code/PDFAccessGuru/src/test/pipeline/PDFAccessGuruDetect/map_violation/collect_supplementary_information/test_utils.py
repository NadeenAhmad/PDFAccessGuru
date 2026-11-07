

from pathlib import Path


def generate_resource_path(path: str) -> str:
    """
    Helper method to generate the path to a resource file given its relative path.
    The resource files are located in src/test/resources/.
    Arguments:
        path: relative path of the resource file relative to src/test/resources/
    Returns:
        The absolute path to the resource file as a string.
    """
    return str(Path(__file__).resolve().parents[4] / "resources" / path)