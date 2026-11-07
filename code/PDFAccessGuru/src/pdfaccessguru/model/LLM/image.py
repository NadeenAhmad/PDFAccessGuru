


from dataclasses import dataclass


@dataclass
class Image:
    """
    Represents an image that can be sent to an LLM.

    Attributes:
        image_data: The image data as bytes. Only png images are allowed.
    """    

    image_data: bytes #Change type if useful

    def __init__(self, image_data: bytes):
        """
        Standard constructor for the Image class.
        """
        self.image_data = image_data

    @staticmethod
    def from_image_path(png_path: str) -> "Image":
        """
        Factory method to create an Image from an file path.
        """
        with open(png_path, "rb") as f:
            return Image(image_data=f.read())