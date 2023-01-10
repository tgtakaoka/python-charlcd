from . import Driver


class DebugDriver(Driver):
    def __init__(self):
        super().__init__()

    def command(self, cmd: int) -> "Driver":
        print("command 0x{:02x}".format(cmd))
        return self

    def data(self, val: int) -> "Driver":
        print("command 0x{:02x}".format(val))
        return self
