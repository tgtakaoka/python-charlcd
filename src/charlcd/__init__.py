import time


class Driver(object):
    def __init__(self):
        pass

    def initialize(self) -> bool:
        """Returns True if 8-bit mode is necessary"""
        return True

    def command(self, cmd: int) -> "Driver":
        return self

    def data(self, val: int) -> "Driver":
        return self


# HD44780 compatible instructions
#
# Clear display
_CLEAR_DISPLAY = 0b0000_0001
# Return home
_RETURN_HOME = 0b0000_0010
# Entry mode set
_ENTRY_LEFT = 0b0000_0110
_ENTRY_RIGHT = 0b0000_0100
# Display on/off control
_DISPLAY_CONTROL = 0b0000_1000
_DISPLAY_ENABLE = 0b0000_0100
_CURSOR_SHOW = 0b0000_0010
_CURSOR_BLINK = 0b0000_0001
# Cursor or display shift
_CURSOR_LEFT = 0b0001_0000
_CURSOR_RIGHT = 0b0001_0100
_DISPLAY_LEFT = 0b0001_1000
_DISPLAY_RIGHT = 0b0001_1100
# Function set
_FUNCTION_8BIT = 0b0011_0000
_FUNCTION_4BIT = 0b0010_0000
_FUNCTION_1LINE = 0b0010_0000
_FUNCTION_2LINE = 0b0010_1000
_FUNCTION_5X8 = 0b0010_0000
_FUNCTION_5X10 = 0b0010_0100
# Set CGRAM address
_CGRAM_ADDRESS = 0b0100_0000
# Set DDRAM address
_DDRAM_ADDRESS = 0b1000_0000


class CharLCD(object):
    """Base character LCD controller, such as HD44780 or ST7066U.

    Attributes:

    """

    def __init__(self, driver: Driver, columns: int, lines: int, row_offsets: list = None):
        """
        Args:
            driver (Driver):
            columns (int):
            lines (int):
        """
        self._driver = driver
        self._columns = columns
        self._lines = lines
        if not row_offsets:
            row_offsets = [0x00, 0x40]
        if len(row_offsets) < lines:
            raise ValueError()
        self._row_offsets = row_offsets
        self._reset()
        self._initialize()

    def _reset(self) -> None:
        """Reset instance variables"""
        self._display_control = _DISPLAY_CONTROL
        self._cgram_address = 0
        self._ddram_address = 0
        self._column, self._row = 0, 0
        self._message = ""
        self._column_align = False
        self._right_to_left = False

    def _initialize(self) -> None:
        # Reset unknown bus state to 8bit mode
        self._driver.command(_FUNCTION_8BIT)
        time.sleep(0.004)
        self._driver.command(_FUNCTION_8BIT)
        time.sleep(0.001)
        # Initialize internal register copy
        self._function_set = _FUNCTION_1LINE | _FUNCTION_5X8
        if self._driver.initialize():
            self._function_set |= _FUNCTION_8BIT
        if self._lines == 2:
            self._function_set |= _FUNCTION_2LINE
        # Issue initialize commands
        self._driver.command(self._function_set)
        self.display = True
        self.clear()
        self._right_to_left = False

    @property
    def driver(self) -> Driver:
        return self._driver

    def clear(self) -> "CharLCD":
        self._driver.command(_CLEAR_DISPLAY)
        self._column, self._row = 0, 0
        time.sleep(0.002)
        return self

    def home(self) -> "CharLCD":
        self._driver.command(_RETURN_HOME)
        self._column, self._row = 0, 0
        time.sleep(0.002)
        return self

    @property
    def right_to_left(self) -> bool:
        return self._right_to_left

    @right_to_left.setter
    def right_to_left(self, enable: bool) -> None:
        self._right_to_left = bool(enable)
        entry = _ENTRY_RIGHT if self._right_to_left else _ENTRY_LEFT
        self._driver.command(entry)

    def _set_disply_control(self, field: int, set_reset: bool) -> int:
        mode = self._display_control
        self._display_control = (mode | field) if set_reset else (mode & ~field)
        self._driver.command(self._display_control)

    @property
    def display(self) -> bool:
        return bool(self._display_control & _DISPLAY_ENABLE)

    @display.setter
    def display(self, enable: bool) -> None:
        self._set_disply_control(_DISPLAY_ENABLE, enable)

    @property
    def cursor(self) -> bool:
        return bool(self._display_control & _CURSOR_SHOW)

    @cursor.setter
    def cursor(self, show: bool) -> None:
        self._set_display_control(_CURSOR_SHOW, show)

    @property
    def blink(self) -> bool:
        return bool(self._display_control & _CURSOR_BLINK)

    @blink.setter
    def cursor(self, blink: bool) -> None:
        self._set_display_control(_CURSOR_BLINK, blink)

    def display_left(self) -> "CharLCD":
        self._driver.command(_DISPLAY_LEFT)
        return self

    def display_right(self) -> "CharLCD":
        self._driver.command(_DISPLAY_RIGHT)
        return self

    def cursor_left(self) -> "CharLCD":
        self._driver.command(_CURSOR_LEFT)
        return self

    def cursor_right(self) -> "CharLCD":
        self._driver.command(_CURSOR_RIGHT)
        return self

    def cursor_position(self, column: int, row: int) -> "CharLCD":
        if column < 0:
            column = 0
        elif column >= self._columns:
            column = self._columns - 1
        if row < 0:
            row = 0
        elif row >= self._lines:
            row = self._lines - 1
        ddram_address = self._row_offsets[row] + column
        self._driver.command(_DDRAM_ADDRESS | ddram_address)
        return self

    @property
    def column_align(self) -> bool:
        return self._column_align

    @column_align.setter
    def column_align(self, enable: bool) -> None:
        self._column_align = bool(enable)

    @property
    def message(self) -> str:
        return self._message

    @message.setter
    def message(self, message: str) -> "CharLCD":
        self._message = message
        line = self._row
        for index, character in enumerate(message):
            col = self._column
            if index == 0 and self._right_to_left:
                col = self._columns - col - 1
                self.cursor_position(col, line)
            if character == "\n":
                line += 1
                col = self._column
                if self._right_to_left:
                    if not self._column_align:
                        col = self._columns - 1
                else:
                    if not self._column_align:
                        col = 0
                self.cursor_position(col, line)
            else:
                self._driver.data(ord(character))
        return self

    def create_character(self, code: int, dots: [int]) -> "CharLCD":
        code &= 7
        self._driver.command(_CGRAM_ADDRESS | (code << 3))
        for i in range(8):
            self._driver.data(dots[i])


# Select instruction table
_FUNCTION_TABLE0 = 0b0010_0000
_FUNCTION_TABLE1 = 0b0010_0001
# Instruction table 1
# Bias Set
_BIAS_SET = 0b0001_0100
_BIAS_1_4 = 0b0000_1000
_BIAS_1_5 = 0b0000_0000
_BIAS_3LINE = 0b0000_0001
# Set ICON address
_ICON_ADDRESS = 0b0100_0000
# Power/ICON Control/Contrast Set
_POWER_SET = 0b0101_0000
_ICON_ON = 0b0000_1000
_BOOSTER_ON = 0b0000_0100
# Follower Control
_FOLLOWER_ON = 0b0110_1000
_FOLLOWER_OFF = 0b0110_0000
# Contrast Set
_CONTRAST_LO = 0b0111_0000


class ExtCharLCD(CharLCD):
    """Extended character LCD controller, such as ST7032 or ST7036"""

    def __init__(self, driver: Driver, columns: int, lines: int, row_offsets: list = None):
        super().__init__(driver, columns, lines, row_offsets)

    def _reset(self) -> None:
        super()._reset()
        self._bias_set = _BIAS_SET
        self._power_set = 0
        self._follower = -1

    def _initialize(self) -> None:
        # Reset unknown bus state to 8bit mode
        self._driver.command(_FUNCTION_8BIT)
        time.sleep(0.004)
        self._driver.command(_FUNCTION_8BIT)
        time.sleep(0.001)
        # Initialize internal register copy
        self._function_set = _FUNCTION_1LINE | _FUNCTION_5X8
        self._bias_set = _BIAS_SET | _BIAS_1_5
        self._power_set = _BOOSTER_ON
        self._icon_address = 0
        if self._driver.initialize():
            self._function_set |= _FUNCTION_8BIT
        if self._lines >= 2:
            self._function_set |= _FUNCTION_2LINE
        if self._lines == 3:
            self._bias_set |= _BIAS_3LINE
        # Issue initialize commands
        self._driver.command(_FUNCTION_TABLE1 | self._function_set)
        self._driver.command(self._bias_set)
        self.contrast = 0b10_0011
        self.follower = 4
        time.sleep(0.200)
        self._driver.command(_FUNCTION_TABLE0 | self._function_set)
        self.display = True
        self.clear()
        self.right_to_left = False

    @property
    def icon_address(self) -> int:
        return self._icon_address

    @icon_address.setter
    def icon_address(self, address: int) -> None:
        address &= 0b1111
        self._icon_address = address
        self._driver.command(_ICON_ADDRESS | address)

    @property
    def icon(self) -> bool:
        return bool(self._power_set & _ICON_ON)

    @icon.setter
    def icon(self, enable: bool) -> None:
        if enable:
            self._power_set |= _ICON_ON
        else:
            self._power_set &= ~_ICON_ON
        self._driver.command(_POWER_SET | self._power_set)

    @property
    def booster(self) -> bool:
        return bool(self._power_set & _BOOSTER_ON)

    @booster.setter
    def booster(self, enable: bool) -> None:
        if enable:
            self._power_set |= _BOOSTER_ON
        else:
            self._power_set &= ~_BOOSTER_ON
        self._driver.command(_POWER_SET | self._power_set)

    @property
    def contrast(self) -> int:
        return self._contrast

    @contrast.setter
    def contrast(self, contrast: int) -> None:
        if contrast < 0:
            contrast = 0
        elif contrast >= 0b11_1111:
            contrast = 0b11_1111
        self._contrast = contrast
        self._driver.command(_CONTRAST_LO | (contrast & 0b1111))
        contrast >>= 4
        self._driver.command(_POWER_SET | self._power_set | contrast)

    @property
    def follower(self) -> int:
        return self._follower

    @follower.setter
    def follower(self, amp: int) -> None:
        if amp < 0:
            self._follower = -1
            self._driver.command(_FOLLOWER_OFF)
            return
        elif amp >= 8:
            amp = 7
        self._follower = amp
        self._driver.command(_FOLLOWER_ON | self._follower)
