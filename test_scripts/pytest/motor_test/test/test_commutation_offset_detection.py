"""
Commutation Offset Detection tests
"""
import time
import logging
import pytest
import oscmd_helpers
from random import choice
from typing import Any, Dict
from enum import Enum, unique
import toolbox as stb
from profiler_helpers import ProfilePositionHandler

logger = logging.getLogger(__name__)


@unique
class OffsetDetectionState(Enum):
    OFFSET_INVALID = 0
    IN_PROGRESS = 1
    OFFSET_VALID = 2


def check_for_error(sc, od):
    if sc.has_fault():
        error_description = od.error_report_description()
        sc.fault_reset()
        return error_description
    return None


@pytest.fixture(scope='class')
def lookup(device_list) -> Dict[Any, Dict[Any, Any]]:
    """Retrieve some useful data before the tests start, to configure the tests."""
    lookup = {}
    logger.info("Discovered %s devices", len(device_list))
    devices_names_in_chain = []
    devices_position_in_chain = []
    for device in device_list:
        od = device['object_dictionary']
        device_name = device['hardware_description']['device']['name']
        devices_names_in_chain.append(device_name)
        device_address = device['info'].device_address
        lookup[device_address] = dict()
        lookup[device_address]['device_position'] = device['info'].position
        devices_position_in_chain.append(device['info'].position)
        lookup[device_address]['device_name'] = device_name

        value_before_test = dict()
        value_before_test['commutation_angle_offset'] = od.commutation_angle_offset()
        value_before_test['commutation_offset_measurement_method'] = od.commutation_offset_measurement_method()
        lookup[device_address]['value_before_test'] = value_before_test

        # Get the position controller encoder resolution
        encoder_config_object_index = stb.get_motion_encoder_config_index(od, position_control=True)
        resolution = od.parameter(encoder_config_object_index, 3)
        lookup[device_address]['resolution'] = resolution

        # Get the commutation offset angle
        commutation_angle_offset_in_od = od.commutation_angle_offset()
        lookup[device_address]['commutation_angle_offset'] = commutation_angle_offset_in_od

        # Get number of pole pairs
        pole_pairs = od.motor_specific_settings_pole_pairs()
        lookup[device_address]['pole_pairs'] = pole_pairs

        # Get commutation offset detection state
        state = od.commutation_offset_state()
        lookup[device_address]['state'] = state

    for i in range(len(devices_names_in_chain)):
        logger.info('{} at position {}'.format(devices_names_in_chain[i], devices_position_in_chain[i]))

    return lookup


def restore_object_dictionary(od, sc, lookup, device_address):
    """
    Restore the original object values back into the OD from the lookup.
    This will reset any objects that have been changed during the
    course of the test to it's original value.
    Resets the drive configuration in the end to force update the OD config.

    Parameters
    ----------
    od
        Object Dictionary
    sc
        State Control
    device_address : int
        Address of the connected device
    lookup : Dict
        Table containing important data of the test

    Note
    -------
    The drive configuration has to be reset at the end because not all objects
    are dynamically updated when changed.
    """
    value_before_test = lookup[device_address]['value_before_test']
    od.commutation_angle_offset(value_before_test['commutation_angle_offset'])
    od.commutation_offset_measurement_method(value_before_test['commutation_offset_measurement_method'])
    stb.reload_drive_configuration(sc)  # For those objects that are not dynamically updated


@pytest.fixture()
def cleanup(mmw, device_list, lookup):
    yield

    logging.debug("Clean up")

    for dev in device_list:
        od = dev['object_dictionary']
        sc = dev['state_control']
        # Disable drive
        sc.fault_reset()
        sc.shutdown()
        device_address = dev['info'].device_address
        restore_object_dictionary(od, sc, lookup, device_address)


class TestCommutationOffsetDetection:
    """Verifies the offset detection procedure.
    """

    def test_commutation_offset_detection(self, mmw, device_list, lookup, cleanup):
        """
        Commutation Offset Detection procedure is run and offset is verified.
        
        checks the precision of commutation angle offset detection.

        How does the test work:
        This test divides 360 mechanical degrees into N sections. By using position
        controller, it puts the rotor at the start of each section. After that,
        position controller is disabled, and offset detection procedure is started
        to find the offset.
        In the first round of offset measurements, "method 0" of offset detection is
        used, and after the first round, the average of found offsets is considered
        as ideal offset

        Methods 1 and 2 of offset detection are also set, and with a similar
        procedure offset is found with these methods.

        The error of all found values is calculated while having the
        "ideal offset" (which was calculated while offset detection method 0 was
        active)

        The test passes if the error of offset detection is always less than 7
        electric degrees for method 0 and method 1.

        Important:
                Before the test is started, the following parameters should be existing
                in object dictionary (saved in config.csv file):
                - position controller should be tuned, and its parameters
                  should be saved in config.csv
                - "phase_order" parameter should be found and saved in object dictionary
                - parameters of "phasing controller" for offset detection method 1 should be
                also saved in the Drive
        """

        for device in device_list:
            od = device['object_dictionary']
            sc = device['state_control']
            device_address = device['info'].device_address
            mechanical_single_turn_resolution = lookup[device_address]['resolution']
            electrical_angle_resolution = 4096
            device_position = lookup[device_address]['device_position']
            device_name = lookup[device_address]['device_name']
            logger.info('running on {} at position {}'.format(device_name, device_position))

            # Check that the state is not In progress
            initial_state = lookup[device_address]['state']
            assert initial_state == OffsetDetectionState.OFFSET_VALID.value, \
                "Commutation offset state is {}. That's not a valid initial state for {} at position {}.".format(
                 OffsetDetectionState(initial_state).name, device_name, device_position)

            # Configure position profiler
            pph = ProfilePositionHandler(sc, od)
            acceleration = 1000  # rpm/s at the motor shaft
            deceleration = 1000  # rpm/s at the motor shaft
            max_velocity = 1000  # rpm at the motor shaft
            target_tolerance = round(0.1 * mechanical_single_turn_resolution)  # tolerance is 30% of resolution
            profiler_timeout = 10
            pph.set_profiler_configuration(pph.VELOCITY_PARAMETERS_FRAME.MOTOR_SHAFT_FRAME, acceleration, deceleration,
                                           max_velocity, target_tolerance, profiler_timeout)
            coh = somanet_oscmd_helpers.CommutationOffsetMeasurementHandler(od)

            original_offset_value = lookup[device_address]['commutation_angle_offset']

            # Move to a set of mechanical positions before starting offset detection
            number_of_mechanical_starting_positions = lookup[device_address]['pole_pairs'] * 1

            method_0_offset_detection_error_degrees = []
            method_1_offset_detection_error_degrees = []
            method_2_offset_detection_error_degrees = []

            method_0_measured_offset_degree_list = []
            method_1_measured_offset_degree_list = []
            method_2_measured_offset_degree_list = []

            # Run offset detection method 0, and after it use the results as a good
            # estimation of commutation angle offset

            offset_detection_method = 0
            logging.debug("COMMUTATION ANGLE OFFSET DETECTION - Method: {}".format(offset_detection_method))
            od.commutation_offset_measurement_method(offset_detection_method)

            for i in range(number_of_mechanical_starting_positions):

                target_position = int(mechanical_single_turn_resolution * i / number_of_mechanical_starting_positions)

                # set commutation angle offset to its original value because
                od.commutation_offset_measurement_method(offset_detection_method)
                od.commutation_angle_offset(original_offset_value)
                stb.reload_drive_configuration(sc)

                # move to different starting positions before offset detection
                pph.set_op_mode()
                expected_position = target_position

                # disengage brake
                od.brake_options_brake_status(2)
                time.sleep(0.2)

                pph.enable_profiler()
                pph.go_to_position(target_position, expected_position)

                sc.set_op_mode(sc.OP_MODES.COMMUTATION_OFFSET)
                sc.enable_operation()

                # disengage brake
                od.brake_options_brake_status(2)
                time.sleep(0.2)

                coh.start_procedure()
                angle_offset = coh.check_response()
                logger.debug("Starting point: {} [Degree Mechanical] \t offset: {} [Ticks] = {: 0.1f} [Degree Electric]"
                             .format(int(target_position * 360 / mechanical_single_turn_resolution), angle_offset,
                                     angle_offset * 360 / electrical_angle_resolution))

                method_0_measured_offset_degree_list.append(angle_offset * 360 / electrical_angle_resolution)

            average_method_0_measured_offset_degree = \
                sum(method_0_measured_offset_degree_list) / len(method_0_measured_offset_degree_list)
            logger.debug("average_method_0_measured_offset_degree: {: 0.1f}".format(
                average_method_0_measured_offset_degree))

            for i in range(len(method_0_measured_offset_degree_list)):
                offset_error_degrees = method_0_measured_offset_degree_list[i] - average_method_0_measured_offset_degree
                method_0_offset_detection_error_degrees.append(offset_error_degrees)

            for offset_detection_method in range(1, 3, 1):
                logging.debug("COMMUTATION ANGLE OFFSET DETECTION - Method: {}".format(offset_detection_method))

                for i in range(number_of_mechanical_starting_positions):

                    target_position = int(mechanical_single_turn_resolution * i /
                                          number_of_mechanical_starting_positions)

                    # set commutation angle offset to its original value because
                    od.commutation_offset_measurement_method(offset_detection_method)
                    od.commutation_angle_offset(original_offset_value)
                    stb.reload_drive_configuration(sc)

                    # move to different starting positions before offset detection
                    pph.set_op_mode()
                    expected_position = target_position

                    # disengage brake
                    od.brake_options_brake_status(2)
                    time.sleep(0.2)

                    pph.enable_profiler()
                    pph.go_to_position(target_position, expected_position)

                    sc.set_op_mode(sc.OP_MODES.COMMUTATION_OFFSET)
                    sc.enable_operation()

                    # disengage the brake for the cases which need to move the rotor
                    if offset_detection_method is 2:
                        # engage brake
                        od.brake_options_brake_status(1)
                        time.sleep(0.2)
                    else:
                        # disengage brake
                        od.brake_options_brake_status(2)
                        time.sleep(0.2)

                    coh.start_procedure()
                    angle_offset = coh.check_response()
                    logger.debug(
                        "Starting point: {} [Degree Mechanical] \t offset: {} [Ticks] = {: 0.1f} [Degree Electric]".
                        format(int(target_position * 360 / mechanical_single_turn_resolution), angle_offset,
                               angle_offset * 360 / electrical_angle_resolution))

                    if offset_detection_method is 1:
                        method_1_measured_offset_degree_list.append(angle_offset * 360 / electrical_angle_resolution)
                    elif offset_detection_method is 2:
                        method_2_measured_offset_degree_list.append(angle_offset * 360 / electrical_angle_resolution)

            for i in range(len(method_1_measured_offset_degree_list)):
                offset_error_degrees = method_1_measured_offset_degree_list[
                                           i] - average_method_0_measured_offset_degree
                method_1_offset_detection_error_degrees.append(offset_error_degrees)

            for i in range(len(method_2_measured_offset_degree_list)):
                offset_error_degrees = method_2_measured_offset_degree_list[
                                           i] - average_method_0_measured_offset_degree
                method_2_offset_detection_error_degrees.append(offset_error_degrees)

            logger.debug("method_0_offset_detection_error_degrees: {}".format(method_0_offset_detection_error_degrees))
            logger.debug("method_1_offset_detection_error_degrees: {}".format(method_1_offset_detection_error_degrees))
            logger.debug("method_2_offset_detection_error_degrees: {}".format(method_2_offset_detection_error_degrees))

            # Check for error
            if sc.has_fault():
                error_description = check_for_error(sc, od)
                pytest.fail("Error {} was raised after the commutation offset procedure."
                            .format(error_description))

            # Check for warning
            if sc.has_warning():
                error_description = od.error_report_description()
                logger.warning("A warning is active: %s.", error_description)

            assert abs(max(method_0_offset_detection_error_degrees)) < 7,\
                'method 0 offset detection error is {: 0.1f} degrees (Maximum acceptable value is 7 for {} at' \
                ' position {}.'.format(
                max(method_0_offset_detection_error_degrees), device_name, device_position)

            assert abs(max(method_1_offset_detection_error_degrees)) < 7,\
                'method 1 offset detection error is {: 0.1f} degrees (Maximum acceptable value is 7 for {} at ' \
                'position {}.'.format(
                max(method_1_offset_detection_error_degrees), device_name, device_position)

    @pytest.mark.parametrize("command", [choice(['disable_voltage', 'disable_operation', 'shutdown']), 'quick_stop'])
    def test_commutation_offset_detection_abort(self, mmw, device_list, lookup, cleanup, command):
        """
        Starts offset commutation procedure and aborts it before it's finished.

        :requirements: 5, 6, 19, 428

        starts commutation angle offset and aborts it after 0.1 second and checks if
        os command returns any error. If no error is generated, the test passes
        """
        for device in device_list:
            od = device['object_dictionary']
            sc = device['state_control']
            device_address = device['info'].device_address
            device_position = lookup[device_address]['device_position']
            device_name = lookup[device_address]['device_name']
            logger.info('running on {} at position {}'.format(device_name, device_position))

            # Check that the state is not In progress
            initial_state = lookup[device_address]['state']
            assert initial_state == OffsetDetectionState.OFFSET_VALID.value, \
                "Commutation offset state is {}. That's not a valid initial state on {} at position {}.".format(
                 OffsetDetectionState(initial_state).name, device_name, device_position)

            coh = somanet_oscmd_helpers.CommutationOffsetMeasurementHandler(od)

            original_offset_value = lookup[device_address]['commutation_angle_offset']
            logging.debug("original_offset_value{}".format(original_offset_value))

            # Run offset detection method 0, and abort it in 0.1 seconds
            for offset_detection_method in range(0, 3, 1):
                logging.debug("COMMUTATION ANGLE OFFSET DETECTION - Method: {}".format(offset_detection_method))
                od.commutation_offset_measurement_method(offset_detection_method)

                sc.set_op_mode(sc.OP_MODES.COMMUTATION_OFFSET)
                sc.enable_operation()

                # disengage brake
                od.brake_options_brake_status(2)
                time.sleep(0.2)

                coh.start_procedure()
                time.sleep(0.1)
                sc.shutdown()

                response = coh.check_response()
                logging.debug("response: {}".format(response))

                try:
                    coh.check_response()
                except somanet_oscmd_helpers.OsCommandException as e:
                    logger.warning('os command did not abort properly:' + str(e))
