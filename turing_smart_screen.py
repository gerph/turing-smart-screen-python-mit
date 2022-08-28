"""
Module for accessing the Turing Smart Screen.

The Turing Smart Screen is a 3.5" external display which is accessed by serial
protocol. It is a slow update device, so is useful for static or slowly updating
displays.

It seems to come in 2 models. A model that has exposed rear, and a model that
is more enclosed and includes rear lights.

The original interfaces was decoded and published at:
    https://github.com/mathoudebine/turing-smart-screen-python

This code is a re-write using none of the original code, which is placed under
the less restrictive MIT license.

---

Copyright 2022, Gerph

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import struct
import time


class TuringError(Exception):
    pass


class TuringProtocolError(TuringError):
    pass


class TuringDisplayBase(object):
    ORIENTATION_PORTRAIT = 0
    ORIENTATION_LANDSCAPE = 1

    # Dimensions of the display, assuming portrait orientation
    WIDTH = 320
    HEIGHT = 480

    def __init__(self, device):
        self.device = device

        # We remember the orientation so that we can change our coordinates.
        self._orientation = self.ORIENTATION_PORTRAIT

        # We remember the brightness so that we might simulate the display off.
        self._brightness = 0

        # Display enabled state
        self._enable = True

    @property
    def width(self):
        """
        Width of the display, in the orientation selected.
        """
        return self.WIDTH if self._orientation == self.ORIENTATION_PORTRAIT else self.HEIGHT

    @property
    def height(self):
        """
        Height of the display, in the orientation selected.
        """
        return self.HEIGHT if self._orientation == self.ORIENTATION_PORTRAIT else self.WIDTH

    def clear(self):
        """
        Clear the display to black.
        """
        # If it's not implemented we can clear the display if we know the
        # orientation by writing a full screen of 0.
        blank = [(0, 0, 0)] * (self.WIDTH * self.HEIGHT)
        self.update_region(0, 0, self.width, self.height, blank)

    def orientation(self, state):
        """
        Set the orientation of the data sent to the display.

        @param state: Orientation to apply (ORIENTATION_PORTRAIT or ORIENTATION_LANDSCAPE)
        """
        self._orientation = state
        raise NotImplementedError("{}.orientation is not implemented".format(self.__class__.__name__))

    def backlight(self, red, green, blue):
        """
        Change the coloured back light.

        @param red:     Red component (0-255)
        @param green:   Green component (0-255)
        @param blue:    Blue component (0-255)
        """
        raise NotImplementedError("{}.backlight is not implemented".format(self.__class__.__name__))

    def enable(self, state):
        """
        Control whether the display is showing or not.

        @param enable:  Whether the display is on or not
        """
        self._enable = state
        raise NotImplementedError("{}.enable is not implemented".format(self.__class__.__name__))

    def brightness(self, scale):
        """
        Change the brightness of the display.

        @param brightness:  How bright to make the display (0 = off, 255 = brightest)
        """
        self._brightness = scale
        raise NotImplementedError("{}.brightness is not implemented".format(self.__class__.__name__))

    def update_region(self, x, y, width, height, rgb_data):
        """
        Update a region of the display with some RGB data.

        @param x, y:            Top left coordinates to plot at
        @param width, height:   Size of the data supplied
        @param rgb:             List of pixel values in tuples of 8 bit (R, G, B) values,
                                in row-major format (ie across the width, first)
        """
        raise NotImplementedError("{}.update_region is not implemented".format(self.__class__.__name__))

    def update_region_pillow(self, x, y, image, x0=0, y0=0, width=None, height=None):
        """
        Helper function to update the region using whole PIL/Pillow image.

        @param x, y:            Top left coordinates to plot at
        @param x0, y0:          Source position to take from in the image
        @param width, height:   Size of the data to plot

        @note: Assumes that the data is in the format RGB, RGBX, RGBA or RGBa.
               Alpha channel is ignored.
        """

        full_rgb_data = image.load()

        if width is None:
            width = image.size[0]
        if height is None:
            height = image.size[1]

        x1 = max(x0 + width, image.size[0])
        y1 = max(y0 + height, image.size[1])

        # Extract the data region from the image supplied into the tuple format
        # we support. It happens that the return from Pillow is accessible as an
        # indexed R, G, B value, so there's no need to create a separate tuple.
        rgb_data = []
        for row in range(y0, y1):
            for col in range(x0, x1):
                rgb_data.append(full_rgb_data[col, row])

        self.update_region(x, y, x1 - x0, y1 - y0, rgb_data)


class TuringDisplayVariant2(TuringDisplayBase):

    CMD_HELLO = 0xca
    CMD_SET_ORIENTATION = 0xcb
    CMD_UPDATE_BITMAP = 0xcc
    CMD_SET_BACKLIGHT = 0xcd
    CMD_SET_BRIGHTNESS = 0xce

    INTER_BITMAP_DELAY = 0.01

    def __init__(self, device):
        super(TuringDisplayVariant2, self).__init__(device)

        # The variant 2 device has a protocol that responds when a 'HELLO'
        # packet is sent.
        hello = bytearray(b'HELLO')
        self.send_command(self.CMD_HELLO, payload=hello)

        response = device.read(10)

        if len(response) != 10:
            raise TuringProtocolError("TuringDisplay serial device not recognised (short response to HELLO)")
        if response[0] != self.CMD_HELLO or response[-1] != self.CMD_HELLO:
            raise TuringProtocolError("TuringDisplay serial device not recognised (bad framing)")
        if response[1:6] != hello:
            raise TuringError("TuringProtocolDisplay serial device not recognised (No HELLO; got %r)" % (response[1:6],))

    def send_command(self, cmd, payload=None):
        if payload is None:
            payload = [0] * 8
        if len(payload) < 8:
            payload = list(payload) + [0] * (8 - len(payload))

        data = bytearray(1)
        data[0] = cmd
        data.extend(payload)
        data.append(cmd)

        self.device.write(bytes(data))

    def orientation(self, state):
        """
        Set the orientation of the data sent to the display.

        @param state: Orientation to apply (ORIENTATION_PORTRAIT or ORIENTATION_LANDSCAPE)
        """
        assert state in (self.ORIENTATION_PORTRAIT, self. ORIENTATION_LANDSCAPE), "Orientation must be one of ORIENTATION_PORTRAIT or ORIENTATION_LANDSCAPE"
        self._orientation = state

        # The constants map to the parameters the device uses, so we can pass through
        self.send_command(self.CMD_SET_ORIENTATION, payload=[state])

    def backlight(self, red, green, blue):
        """
        Change the coloured back light.

        @param red:     Red component (0-255)
        @param green:   Green component (0-255)
        @param blue:    Blue component (0-255)
        """
        assert 0 <= red < 256, "Backlight red must be between 0 and 255 inclusive"
        assert 0 <= green < 256, "Backlight green must be between 0 and 255 inclusive"
        assert 0 <= blue < 256, "Backlight blue must be between 0 and 255 inclusive"
        self.send_command(self.CMD_SET_BACKLIGHT, payload=[red, green, blue])

    def enable(self, state):
        """
        Control whether the display is showing or not.

        @param enable:  Whether the display is on or not
        """
        state = bool(state)

        if self._enable != state:
            if state:
                self.send_command(self.CMD_SET_BRIGHTNESS, payload=[self._brightness])
            else:
                self.send_command(self.CMD_SET_BRIGHTNESS, payload=[0])

        self._enable = state

    def brightness(self, scale):
        """
        Change the brightness of the display.

        @param brightness:  How bright to make the display (0 = off, 255 = brightest)
        """
        assert 0 <= scale < 256, "Brightness must be between 0 and 255 inclusive"
        self._brightness = scale
        if self._enable:
            # Only send the display brightness if we're enabled
            self.send_command(self.CMD_SET_BRIGHTNESS, payload=[scale])

    def update_region(self, x, y, width, height, rgb_data):
        """
        Update a region of the display with some RGB data.

        @param x, y:            Top left coordinates to plot at
        @param width, height:   Size of the data supplied
        @param rgb_data:        List of pixel values in tuples of 8 bit (R, G, B) values,
                                in row-major format (ie across the width, first)
        """
        assert len(rgb_data) >= width * height, "Not enough data supplied to update region of {}x{} (only {} pixels present)".format(width, height, len(rgb_data))
        x1 = x + width - 1
        y1 = y + height - 1
        self.send_command(self.CMD_UPDATE_BITMAP,
                          payload=[(x>>8) & 255, (x & 255),
                                   (y>>8) & 255, (y & 255),
                                   (x1>>8) & 255, (x1 & 255),
                                   (y1>>8) & 255, (y1 & 255)])

        # We want to write out reasonable chunk of data at a time so that it
        # can be streaming out whilst we're accumulating more data.
        flush_size = self.WIDTH * 8
        accumulator = []
        for start in range(0, width * height, flush_size):
            for colour in rgb_data[start:start + flush_size]:
                r = colour[0] >> 3
                g = colour[1] >> 2
                b = colour[2] >> 3
                halfword = struct.pack('>H', (r<<11) | (g<<5) | b)
                accumulator.append(halfword)

            self.device.write(b''.join(accumulator))
            accumulator = []

        if accumulator:
            self.device.write(b''.join(accumulator))

        # A delay is required between sending the data and the next command.
        time.sleep(self.INTER_BITMAP_DELAY)
