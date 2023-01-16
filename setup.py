import sys
from setuptools import find_packages, setup

from qio import (
    __author__,
    __description__,
    __email__,
    __license__,
    __title__,
    __url__,
    __version__,
)

PY36 = sys.version_info < (3, 7)


minimal_requirements = [
    "bottle==0.12.*",
    "click%s" % ("==8.0.4" if PY36 else ">=8.0.4,<9"),
    "colorama",
    "marshmallow==%s" % ("3.14.1" if PY36 else "3.*"),
    "pyelftools>=0.27,<1",
    "pyserial==3.5.*",  # keep in sync "device/monitor/terminal.py"
    "requests==2.*",
    "requests==%s" % ("2.27.1" if PY36 else "2.*"),
    "semantic_version==2.10.*",
    "tabulate==%s" % ("0.8.10" if PY36 else "0.9.*"),
]

home_requirements = [
    "aiofiles==%s" % ("0.8.0" if PY36 else "22.1.*"),
    "ajsonrpc==1.*",
    "starlette==%s" % ("0.19.1" if PY36 else "0.23.*"),
    "uvicorn==%s" % ("0.16.0" if PY36 else "0.20.*"),
    "wsproto==%s" % ("1.0.0" if PY36 else "1.2.*"),
]

setup(
    name=__title__,
    version=__version__,
    description=__description__,
    # long_description=open("qio.rst").read(),
    author=__author__,
    author_email=__email__,
    url=__url__,
    license=__license__,
    install_requires=minimal_requirements + home_requirements,
    python_requires=">=3.6",
    packages=find_packages(include=["platformio", "platformio.*"]),
    package_data={
        "platformio": [
            "assets/system/99-platformio-udev.rules",
            "assets/templates/ide-projects/*/*.tpl",
            "assets/templates/ide-projects/*/.*.tpl",  # include hidden files
            "assets/templates/ide-projects/*/.*/*.tpl",  # include hidden folders
        ]
    },
    entry_points={
        "console_scripts": [
            "platformio = platformio.__main__:main",
            "pio = platformio.__main__:main",
            "piodebuggdb = platformio.__main__:debug_gdb_main",
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: C",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Compilers",
    ],
    keywords=[
        "iot",
        "embedded",
        "arduino",
        "mbed",
        "esp8266",
        "esp32",
        "fpga",
        "firmware",
        "continuous-integration",
        "cloud-ide",
        "avr",
        "arm",
        "ide",
        "unit-testing",
        "hardware",
        "verilog",
        "microcontroller",
        "debug",
    ],
)
