from .error import *
from typing import Optional, List
from easyhid import Enumeration
from PIL import Image
from time import sleep
from threading import Thread

class Device:
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

        self.device = devices[0]
        self.thread = None
        self.device.open()

    def __send_image_to_device(self, image):
        """Sends image to the device, in the form of a bytearray, private method"""
        self.device.send_feature_report(bytearray([0x61]) + image.tobytes() + bytearray([0x00]))

    def __gif_thread(self, frames, fps):
        """Thread to show GIF on the device, private method"""
        for frame in frames:
            if self.thread == None:
                break
            self.__send_image_to_device(frame)
            sleep(1/fps)

    def __convert_img_to_bw(self, img, dither):
        """Convert image to black and white, private method"""
        if dither:
            return img.convert(mode = "1")
        else:
            return img.convert(mode = "1", dither = Image.Dither.NONE)

    def __stretch_resize_image(self, img: Image.Image, stretch):
        """Stretch or resize image, private method"""
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

    def send(self, image: Image.Image, stretch: Optional[bool] = True, dither: Optional[bool] = True, fps: Optional[float] = 25) -> Thread:
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
        
        Exceptions:
            ioled.error.IsNotAnImage: Raised if the image parameter is not an instance of PIL.Image.Image
            ioled.error.AlreadyAThreadRunning: Raised if there already is a gif running
        """
        if isinstance(image, Image.Image):
            if not image.is_animated:
                image = self.__stretch_resize_image(image, stretch)
                image = self.__convert_img_to_bw(image, dither)
                
                self.__send_image_to_device(image)
            elif self.thread == None:
                frames = []
                index = 0
                print(image.n_frames)
                try:
                    while True:
                        image.seek(index)
                        print(f"{index} {image.size}")
                        
                        frame = image.copy()
                        frame = self.__stretch_resize_image(frame, stretch)
                        frame = self.__convert_img_to_bw(frame, dither)
                        frames.append(frame)
                        index = image.tell() + 1
                except EOFError:
                    pass
                thread = Thread(target = self.__gif_thread, args = (frames, fps))
                self.thread = thread
                thread.start()
                return thread
            else:
                raise AlreadyAThreadRunning
        else:
            raise IsNotAnImage(image)
            

    def clear(self):
        """Clears the screen of any image and stops any GIF running"""
        if self.thread != None:
            self.thread = None
        self.device.send_feature_report(bytearray([0x61] + [0x00] * 641))
