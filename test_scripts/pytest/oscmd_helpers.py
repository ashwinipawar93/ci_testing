"""
SOMANET OS command helpers

Contains the helpers to use OS command, as well as helpers for each of the commands.
"""

__author__ = "Synapticon GmbH"
__copyright__ = "Copyright 2019, Synapticon GmbH"
__license__ = "Closed"
__email__ = "support@synapticon.com"

import time
import pytest
import logging

from enum import Enum, unique


class OsCommandException(Exception):
    """Exception for operations that just didn't work."""
    pass

@unique
class OsCmdModes(Enum):
    EXECUTE_NEXT_CMD = 0
    ABORT_ALL_CMD = 3


@unique
class OsCmdCommand(Enum):
    ENCODER_REGISTER_COMMUNICATION = 0
    ICMU_CALIBRATION = 1
    OPEN_LOOP_FIELD_MODE = 2
    OSCMD_HRD_STREAMING = 3
    MOTOR_PHASE_ORDER_DETECTION = 4  # Phase order is obtained by OS command 5
    COMMUTATION_OFFSET_MEASUREMENT = 5
    OPEN_PHASE_DETECTION = 6
    POLE_PAIR_DETECTION = 7
    PHASE_RESISTANCE_MEASUREMENT = 8
    PHASE_INDUCTANCE_MEASUREMENT = 9
    TORQUE_CONSTANT_MEASUREMENT = 10
    RESERVED_FOR_EXTENSION_CMD = 255


@unique
class OsCmdStatus(Enum):
    COMPLETED_NOERROR_NOREPLY = 0
    COMPLETED_NOERROR_WITHREPLY = 1
    COMPLETED_WITHERROR_NOREPLY = 2
    COMPLETED_WITHERROR_WITHREPLY = 3
    IN_PROCESS_0 = 100
    IN_PROCESS_100 = 200
    CMD_IN_PROGRESS = 255


@unique
class OsCmdErrorCodes(Enum):
    CMD_NOT_ALLOWED = 251
    CMD_ABORTED = 252
    CMD_TIMEOUT = 253
    UNSUPPORTED_CMD = 254
    RESERVED_FOR_EXTENSION = 255


class OsCmdHandler:
    """Handler to use OS commands.
    """

    MODES = OsCmdModes
    STATUS = OsCmdStatus

    def __init__(self, od):
        self.od = od
        self.current_command = None
        self.current_mode = self.MODES.EXECUTE_NEXT_CMD
        self.status_in_progress = [self.STATUS.CMD_IN_PROGRESS.value] + list(
            range(self.STATUS.IN_PROCESS_0.value, self.STATUS.IN_PROCESS_100.value + 1))

    def change_mode(self, mode):
        """Change OS command mode (0x1024:0).

        Parameters
        ----------
        mode : Enum
            OS command mode to set.
        """
        assert isinstance(mode, OsCmdModes), "OS command mode {} is not valid.".format(mode)
        self.current_mode = mode
        self.od.os_command_mode(mode)

    def execute_command(self, command):
        """Execute a raw OS command.
        A new OS command cannot be executed until the previous one was read with `get_response()` and the returned value
        indicates that the command is finished.

        Parameters
        ----------
        command : List
            List with the raw OS command.
        """
        if self.current_command is not None:
            pytest.fail("OS command request was received when another one was already in progress.")
            return

        self.current_command = command
        """
        question: what is "os_command_command"? where is it defined?
        """
        self.od.os_command_command(bytes(command))

    def get_response(self):
        """Check the current OS command response.

        Returns
        -------
        response : List
            List with the raw OS command response.
        """
        response = list(self.od.os_command_response())
        if response[0] not in self.status_in_progress:
            self.current_command = None
        return response

    def get_active_command(self):
        """Get the currently active OS command.

        Returns
        -------
        current_command : List or None
            Returns the raw OS command if it was not read to be finished. Otherwise returns None.
        """
        return self.current_command


class EncoderRegisterCommunicationHandler:
    """Handler to use encoder register communication.
    """

    def __init__(self, od, timeout=1):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def read_register(self, encoder_connector, register_address, slave_address=0):
        """Send command to read the value of a BiSS register.

        Parameters
        ----------
        encoder_connector : int
            Target encoder connector.
        register_address : int
            Register address to read.
        slave_address : int
            BiSS slave address.
        """
        b0 = OsCmdCommand.ENCODER_REGISTER_COMMUNICATION.value
        b1 = encoder_connector
        b2 = 0 | slave_address << 1
        b3 = register_address
        command = [b0, b1, b2, b3, 0, 0, 0, 0]
        self.och.execute_command(command)

    def write_register(self, encoder_connector, register_address, register_value, slave_address=0):
        """Send command to write the value of a BiSS register.

        Parameters
        ----------
        encoder_connector : int
            Target encoder connector.
        register_address : int
            Register address to write.
        register_value : int
            Register value to write.
        slave_address : int
            BiSS slave address.
        """
        b0 = OsCmdCommand.ENCODER_REGISTER_COMMUNICATION.value
        b1 = encoder_connector
        b2 = 1 | slave_address << 1
        b3 = register_address
        b4 = register_value
        command = [b0, b1, b2, b3, b4, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Register communication response.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                return response[2]
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.ENCODER_REGISTER_COMMUNICATION.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


@unique
class IcmuCalibrationModes(Enum):
    CONFIGURATION_MODE = 0
    RAW_MODE = 1
    STANDARD_MODE = 2


class IcmuCalibrationModeHandler:
    """Handler to enable iC-MU calibration modes.
    """

    def __init__(self, od, timeout=1):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def enable_mode(self, encoder_connector, mode):
        """Send command to set an iC-MU calibration mode.

        Parameters
        ----------
        encoder_connector : int
            Target encoder connector.
        mode : Enum
            iC-MU calibration mode.
        """
        b0 = OsCmdCommand.ICMU_CALIBRATION.value
        b1 = encoder_connector | mode.value << 3
        command = [b0, b1, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : bool
            True if the mode was changed successfully.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_NOREPLY.value:
                return True
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.ICMU_CALIBRATION.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


@unique
class HrdStreamingActions(Enum):
    CONFIGURE_STREAM = 0
    START_STREAM = 1


@unique
class HrdStreamingDataIndex(Enum):
    ENCODER_RAW_DATA = 0


@unique
class OsCmd3ErrorCodes(Enum):
    INITIALIZATION_ERROR = 0
    STREAMING_ERROR = 1
    DURATION_VALUE_ERROR = 2
    DATA_INDEX_VALUE_ERROR = 3


class HrdStreamingHandler:
    """Handler to use High resolution data streaming.
    """

    def __init__(self, od, timeout=5):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def configure_stream(self, data_index, duration_in_ms):
        """Send command to configure the streaming.

        Parameters
        ----------
        data_index : Enum
            Index of the data to stream.
        duration_in_ms : int
            Duration of the stream in milliseconds.
        """
        self.timeout = duration_in_ms * 1000 + 1
        b0 = OsCmdCommand.OSCMD_HRD_STREAMING.value
        b1 = HrdStreamingActions.CONFIGURE_STREAM.value
        b2 = data_index.value
        b3 = (duration_in_ms >> 8) & 0xff
        b4 = duration_in_ms & 0xff
        command = [b0, b1, b2, b3, b4, 0, 0, 0]
        self.och.execute_command(command)

    def start_stream(self):
        """Send command to start the streaming.
        """
        b0 = OsCmdCommand.OSCMD_HRD_STREAMING.value
        b1 = HrdStreamingActions.START_STREAM.value
        command = [b0, b1, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : bool
            True if the mode was changed successfully.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_NOREPLY.value:
                return True
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                elif response[2] in [item.value for item in OsCmd3ErrorCodes]:
                    os_error_code = OsCmd3ErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.OSCMD_HRD_STREAMING.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class PhaseOrderDetectionHandler:
    """Handler to get motor phase order.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.MOTOR_PHASE_ORDER_DETECTION.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Motor phases order.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                motor_phases_order = response[2]
                return motor_phases_order
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.COMMUTATION_OFFSET_MEASUREMENT.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class CommutationOffsetMeasurementHandler:
    """Handler to get the commutation offset and the motor phase order.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        """
        byte 0 is set to 5. 
        I guess byte 0 shows what is the OsCmd
        """
        b0 = OsCmdCommand.COMMUTATION_OFFSET_MEASUREMENT.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int, int
            Angle offset value and motor phases order.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                angle_offset = response[2] << 8 | response[3]
                return angle_offset
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.COMMUTATION_OFFSET_MEASUREMENT.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


@unique
class OsCmd6ErrorCodes(Enum):
    OPEN_TERMINAL_A = 0
    OPEN_TERMINAL_B = 1
    OPEN_TERMINAL_C = 2
    OPEN_FET_A_HIGH = 3
    OPEN_FET_A_LOW = 4
    OPEN_FET_B_HIGH = 5
    OPEN_FET_B_LOW = 6
    OPEN_FET_C_HIGH = 7
    OPEN_FET_C_LOW = 8


class OpenLoopFieldModeHandler:
    """Handler to work with "open loop field mode" feature
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def set_starting_angle_milli_radian(self, angle_start_milli_radian):
        """Set starting angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 0
        value = angle_start_milli_radian
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        self.och.execute_command(command)
        logging.info("sent command: {}".format(command))

    def set_ending_angle_milli_radian(self, angle_end_milli_radian):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 1
        value = angle_end_milli_radian
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))

        self.och.execute_command(command)

    def set_max_rotational_speed_rad_per_second(self, max_rotational_speed_rad_per_second):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 2
        value = max_rotational_speed_rad_per_second
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))
        self.och.execute_command(command)

    def set_rotational_acceleration_rad_per_squared_second(self, rotational_acceleration_rad_per_squared_second):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 3
        value = rotational_acceleration_rad_per_squared_second
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))
        self.och.execute_command(command)

    def set_length_start_per_thousand_rated_current(self, length_start_per_thousand_rated_current):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 4
        value = length_start_per_thousand_rated_current
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))
        self.och.execute_command(command)

    def set_length_end_per_thousand_rated_current(self, length_end_per_thousand_rated_current):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 5
        value = length_end_per_thousand_rated_current
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))
        self.och.execute_command(command)

    def set_length_speed_per_thousand_rated_current_per_second(self, length_speed_per_thousand_rated_current_per_second):
        """Set ending angle of OpenLoopFieldMode profiler in [milli-radian]
        """

        """
        b0 is the index of os_command it shows that os_command_2 which is related to
        open loop field mode is selected
        """
        b0 = 2

        b1 = 6
        value = length_speed_per_thousand_rated_current_per_second
        b5 = value & 0x000000FF
        b4 = (value & 0x0000FF00) >> 8
        b3 = (value & 0x00FF0000) >> 16
        b2 = (value & 0xFF000000) >> 24
        command = [b0, b1, b2, b3, b4, b5, 0, 0]
        logging.info("sent command: {}".format(command))
        self.och.execute_command(command)

    def enable_open_loop_field_mode(self, device):
        """ enable open loop field mode """
        sc = device['state_control']
        sc.disable_operation()
        # Enter OPEN_LOOP_FIELD_MODE
        sc.set_op_mode(sc.OP_MODES.OPEN_LOOP_FIELD_MODE)
        sc.enable_operation()

    def get_response(self):
        """Wait until a response is received or until timeout happens.

           Returns
           -------
           response : int
               Number of pole pairs.
       """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_NOREPLY.value:
                return True
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.OPEN_PHASE_DETECTION.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class OpenPhaseDetectionHandler:
    """Handler to check if there are open phases.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.OPEN_PHASE_DETECTION.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Number of pole pairs.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_NOREPLY.value:
                return True
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                elif response[2] in [item.value for item in OsCmd6ErrorCodes]:
                    os_error_code = OsCmd6ErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.OPEN_PHASE_DETECTION.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class PolePairDetectionHandler:
    """Handler to get the number of pole pairs.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.POLE_PAIR_DETECTION.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Number of pole pairs.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                return response[2]
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.POLE_PAIR_DETECTION.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class PhaseResistanceMeasurementHandler:
    """Handler to get the phase resistance.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.PHASE_RESISTANCE_MEASUREMENT.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Phase resistance.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                phase_resistance = response[2] << 24 | response[3] << 16 | response[4] << 8 | response[5]
                return phase_resistance
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.PHASE_RESISTANCE_MEASUREMENT.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))


class PhaseInductanceMeasurementHandler:
    """Handler to get the phase inductance.
    """

    def __init__(self, od, timeout=60):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.PHASE_INDUCTANCE_MEASUREMENT.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Phase inductance.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                phase_inductance = response[2] << 24 | response[3] << 16 | response[4] << 8 | response[5]
                return phase_inductance
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.PHASE_INDUCTANCE_MEASUREMENT.value, response[0]))

            if time.time() > timeout:
                raise OsCommandException("OS command status was in progress for {} seconds.".format(self.timeout))


class TorqueConstantMeasurementHandler:
    """Handler to get the torque constant.
    """

    def __init__(self, od, timeout=25):
        self.och = OsCmdHandler(od)
        self.timeout = timeout

    def start_procedure(self):
        """Send command to start procedure.
        """
        b0 = OsCmdCommand.TORQUE_CONSTANT_MEASUREMENT.value
        command = [b0, 0, 0, 0, 0, 0, 0, 0]
        self.och.execute_command(command)

    def check_response(self):
        """Wait until a response is received or until timeout happens.

        Returns
        -------
        response : int
            Torque constant.
        """
        timeout = time.time() + self.timeout
        while True:
            response = self.och.get_response()
            time.sleep(0.010)
            if response[0] is OsCmdStatus.COMPLETED_NOERROR_WITHREPLY.value:
                torque_constant = response[2] << 24 | response[3] << 16 | response[4] << 8 | response[5]
                return torque_constant
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_WITHREPLY.value:
                if response[2] in [item.value for item in OsCmdErrorCodes]:
                    os_error_code = OsCmdErrorCodes(response[2]).name
                    raise OsCommandException("OS command returned an error (OS error code {}: {}).".format(
                        response[2], os_error_code))
                else:
                    pytest.fail(
                        "OS command returned an error, but the OS error code is unknown ({}).".format(response[2]))
            elif response[0] is OsCmdStatus.COMPLETED_WITHERROR_NOREPLY.value:
                raise OsCommandException("OS command returned an error (no OS error code).")
            elif response[0] in self.och.status_in_progress:
                pass
            else:
                pytest.fail("Not valid status for OS command {}: {}.".format(
                    OsCmdCommand.TORQUE_CONSTANT_MEASUREMENT.value, response[0]))

            if time.time() > timeout:
                pytest.fail("OS command status was in progress for {} seconds.".format(self.timeout))
