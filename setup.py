from setuptools import setup, find_packages

setup(
    name="i-oled-gg",
    version="1.0.2",
    author="KarlHlmgrn",
    author_email="karlhlmgrn.github@gmail.com",
    description="Simple library to send images or GIFs to a SteelSeries keyboard OLED screen",
    install_requires=[
        "easyhid>=0.0.10",
        "Pillow>=9.4.0"
    ],
    url="https://github.com/KarlHlmgrn/i-oled-gg",
    packages=find_packages()
)
