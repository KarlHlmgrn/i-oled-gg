from enum import IntEnum
from .error import *
from typing import Optional, Tuple
from easyhid import Enumeration, HIDDevice
from PIL import Image, ImageFont, ImageDraw
from time import sleep
from threading import Thread

class Loop(IntEnum):
    ONCE = 1
    TWICE = 2
    VALUE = lambda i: i
    INFINITE = -1

class GGDevice:
    """A class representing an OLED-compatible device with an interface to send images."""
    def __init__(self):
        en = Enumeration()

        devices = en.find(product="SteelSeries Apex Pro", interface=1)
        if not devices:
            devices = en.find(product="SteelSeries Apex Pro TKL", interface=1)
        if not devices:
            devices = en.find(product="SteelSeries Apex 7", interface=1)
        if not devices:
            devices = en.find(product="SteelSeries Apex 7 TKL", interface=1)
        if not devices:
            devices = en.find(product="SteelSeries Apex 5", interface=1)
        
        assert len(devices) == 1

        self.device: HIDDevice = devices[0]
        self.thread = None
        self.current_image = Image.new("1", (128, 40), 0)
        self.device.open()

    def __send_image_to_device(self, image):
        """Sends image to the device, in the form of a bytearray"""
        self.current_image = image
        self.device.send_feature_report(bytearray([0x61]) + image.tobytes() + bytearray([0x00]))

    def __get_image_from_device(self) -> Image.Image:
        return self.current_image

    def __gif_thread(self, frames, fps, loop):
        """Thread to show GIF on the device"""
        for _ in range(loop):
            for frame in frames:
                if self.thread == None:
                    break
                self.__send_image_to_device(frame)
                sleep(1/fps)

    def __convert_img_to_bw(self, img, dither):
        """Convert image to black and white"""
        if dither:
            return img.convert(mode = "1")
        else:
            return img.convert(mode = "1", dither = Image.Dither.NONE)

    def __stretch_resize_image(self, img: Image.Image, stretch):
        """Stretch or resize image"""
        if stretch:
            return img.resize((128, 40), Image.ANTIALIAS)
        else:
            max_width = 128
            max_height = 40
            width = img.size[0]
            height = img.size[1]
            multiplier = min(max_width/width, max_height/height)
            temp_img = Image.new('RGB', (128,40))
            img = img.resize((int(width*multiplier), int(height*multiplier)), Image.ANTIALIAS)
            temp_img.paste(img, box = (int(128/2 - (width*multiplier)/2), int(40/2 - (height*multiplier)/2)))
            return temp_img

    def send(self, image: Image.Image, stretch: Optional[bool] = True, dither: Optional[bool] = True, fps: Optional[float] = 25, loop: Optional[Loop] = Loop.ONCE) -> Thread:
        """
        Send an image or GIF to the device, can raise IsNotAnImage exception

        Args:
            image: PIL.Image.Image
                Image or GIF to send
            stretch: Optional[bool]
                Whether or not to stretch the image to 128x40 pixels
                (Default: True)
            dither: Optional[bool]
                Whether or not to dither the image, making gradients to dots
                (Default: True)
            fps: Optional[float]
                FPS to play gif at, only applicable for GIF images
                (Default: 25.0)
            loop: Optional[Loop]
                Amount of times to loop GIF, only applicable for GIF images
                Can be Loop.ONCE, Loop.TWICE, Loop.INFINITE, Loop.VALUE(int)
                (Default: Loop.ONCE)

        Exceptions:
            ioled.error.IsNotAnImage: Raised if the image parameter is not an instance of PIL.Image.Image
            ioled.error.AlreadyAThreadRunning: Raised if there already is a gif running
        """
        if isinstance(image, Image.Image):
            if not getattr(image, "is_animated", False):
                image = self.__stretch_resize_image(image, stretch)
                image = self.__convert_img_to_bw(image, dither)
                self.__send_image_to_device(image)
            elif not self.is_gif_playing():
                assert loop > 0
                frames = []
                index = 0
                thread = 1
                try:
                    while True:
                        image.seek(index)
                        frame = image.copy()
                        frame = self.__stretch_resize_image(frame, stretch)
                        frame = self.__convert_img_to_bw(frame, dither)
                        frames.append(frame)
                        index = image.tell() + 1
                except EOFError:
                    pass
                thread = Thread(target = self.__gif_thread, args = (frames, fps, loop))
                self.thread = thread
                thread.start()
                return thread
            else:
                raise AlreadyAThreadRunning
        else:
            raise IsNotAnImage(image)

    def paste(self, image: Image.Image, box: Tuple[int, int] = (0, 0), dither: Optional[bool] = True):
        """
        Pastes an image on top of the current image showing, cannot paste on top of a GIF

        Args:
            image: Image.Image
                Image to paste
            box: Union[Tuple[int, int], List[int, int]]
                Top left coordinate to paste the image on
                (Default: (0,0))
            dither: Optional[bool]
                Whether or not to dither the image, making gradients to dots
                (Default: True)
            
        Exception:
            ioled.error.AlreadyAThreadRunning: Raised if a GIF is playing
        """
        if self.thread != None:
            raise AlreadyAThreadRunning
        assert box[1] >= 0 and box[1] < 40 and box[0] >= 0 and box[0] < 128

        image = self.__convert_img_to_bw(image, dither)
        self.current_image.paste(image, box)
        self.__send_image_to_device(self.current_image)
    
    def print(self, text: str, font: ImageFont, box: Tuple[int, int] = (0, 0), fill: int = None, *args, **kwargs):
        """
        Prints text atop the current image

        Args:
            text: str
                Text to print
            font: ImageFont
                Font to print the text with
            box: Union[Tuple[int, int], List[int, int]]
                Top left coordinate to print the text to
                (Default: (0,0))
            fill: int
                Color of the text, int 0 or 255
                (Default: None)
            *args
                Any other arguments for ImageDraw.text()
            **kwargs
                Any other arguments for ImageDraw.text()
        """
        ImageDraw.Draw(self.current_image).text(box, text, fill, font, *args, **kwargs)
        self.__send_image_to_device(self.current_image)

    def is_gif_playing(self):
        return self.thread != None

    def clear(self):
        """Clears the screen of any image and stops any playing GIF"""
        if self.thread != None:
            self.thread = None
        self.device.send_feature_report(bytearray([0x61] + [0x00] * 641))
