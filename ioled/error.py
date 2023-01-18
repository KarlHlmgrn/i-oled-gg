class IsNotAnImage(Exception):
    """Exception raised when image is not an instance of PIL.Image.Image
    
    :param image: The Image object
    """

    def __init__(self, image):
        self.image = image
        self.message = "The image is not an instance of PIL.Image.Image"
        super().__init__(self.message)

    def __str__(self):
        return f"{self.image} -> {self.message}"

class AlreadyAThreadRunning(Exception):
    """Exception raised when a GIF thread is already running"""

    def __init__(self):
        self.message = "A GIF thread is already running, use clear() to stop a running GIF thread"
        super().__init__(self.message)