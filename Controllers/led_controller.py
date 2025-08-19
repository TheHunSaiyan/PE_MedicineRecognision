import serial
import time

from Logger.logger import logger


class LEDController:
    def __init__(self, port: str, baud: int = 115200):
        """
        Initialize the LEDController with serial connection parameters.

        Args:
            port (str): The serial port device path (e.g., '/dev/ttyACM0').
            baud (int, optional): Baud rate for serial communication. 
                                 Defaults to 115200.

        Returns:
            None
        """
        self.ser = None
        self.port = port
        self.baud = baud
        self.success = self.connect_to_device()

    def connect_to_device(self):
        """
        Establish serial connection to the Arduino device.

        Args:
            None

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        if not self.port:
            logger.error("No serial port specified")
            return False

        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            logger.info(
                f"Connected to Arduino on {self.port} at {self.baud} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"Could not open serial port: {e}")
            self.ser = None
            return False

    def set_values(self, brightness: int, pin_number: int):
        """
        Set brightness values for a specific LED pin.

        Args:
            brightness (int): Brightness value (0 or 30-180). 
                            0 turns off the LED, 30-180 sets brightness level.
            pin_number (int): Arduino pin number controlling the LED.
                            Must be 9 (side north), 10 (side south), or 11 (upper).

        Returns:
            None
        """
        if (brightness < 30 or brightness > 180) and brightness != 0:
            logger.warning("Brightness must be between 30 and 180.")
            return
        if pin_number not in (9, 10, 11):
            logger.warning(f"Your pin number is {pin_number}")
            logger.warning(
                "Pin number must be 9 (side north), 10 (side south) or 11 (upper).")
            return
        if not self.ser or not self.ser.is_open:
            logger.warning(
                "Serial connection not open. Attempting to reconnect...")
            self.connect_to_device()
            if not self.ser or not self.ser.is_open:
                logger.error("Failed to reconnect to serial port.")
                return

        try:
            command = f"{brightness} {pin_number}\n"
            self.ser.write(command.encode())
            self.ser.flush()
            logger.info(f"Sent: {command.strip()}")
        except serial.SerialException as e:
            logger.error(f"Serial error: {e}")

    def close(self):
        """
        Close the serial connection to the Arduino device.

        Args:
            None

        Returns:
            None
        """
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial port closed.")
