# Turing Smart Screen Python library

## Introduction

This is an implementation of access to the Turing Smart Screen as a Python library.
It is a complete reimplementation from scratch using none of the code from the
original library at https://github.com/mathoudebine/turing-smart-screen-python but
under MIT license. Some of the methods are similar, because there's only so many
ways you can control these screens, and it's useful to be compatible.

The library is Python 2/3 compatible, as this is required for the project it is
to be integrated with.

## Interface

The interface is through object construction and method operations, to allow it to
be multiply instantiated and to allow us to inherit behaviour for each of the
implementations.

```
from PIL import Image
import serial

ser = serial(DEVICE, 115200, timeout=1, rtscts=1)
display = TuringDisplayAutoSelect(ser)

# Hide everything
display.enable(False)

# If the display is rotated around 180 degrees, it image may been inversion
display.invert(display.INVERT_XY)

# Draw a picture in the display
image = Image.open(bitmap_path)
display.update_region_pillow(0, 0, image)

# And show it in one go
display.enable(True)
```

## License

This library is released under the MIT license. The original was under the
restrictive GPL, which precludes my incorporating it into my projects, so I have
re-implemented the functions and made the system more object oriented.

See [LICENSE] for details.
