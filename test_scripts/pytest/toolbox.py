"""
SOMANET Toolbox (stb)

A collection of high-level utilities that help make writing tests easier.

Design goals
------------

1. Add things here that may be useful to many tests. Otherwise, keep
   marginally useful methods statically defined in the test module itself.
2. Make these as well-performing as possible. It's worth spending time to get them right.
3. Use *TODO* tags to point out limitations
4. Write your utility in such a way that it enforces good testing practices.

Usage
----

It is recommended to use a standard way of importing:
    ``import somanet_toolbox as stb``
"""

import numpy as np
import pytest
import time
import math
import logging
from enum import Enum, unique
from typing import List


def reload_drive_configuration(sc):
    """Do transition 2 to reload drive configuration.

    This will trigger the drive to read the Object dictionary to see if some value changed.
    Some objects don't need this because they are updated continuously.
    """

    if sc.has_fault():
        # If the state is `Fault`, reset fault will reload the configuration.
        sc.fault_reset()
    else:
        # Otherwise, transition 2 will reload the configuration.
        sc.disable_voltage()
        sc.shutdown()


@unique
class SensorFunctions(Enum):
    DISABLED = 0
    COMMUTATION_AND_MOTION_CONTROL_FEEDBACK = 1
    COMMUTATION_AND_MONITORING = 2
    MOTION_CONTROL_FEEDBACK_ONLY = 3
    MONITORING_ONLY = 4
    COMMUTATION_ONLY = 5
    POSITION = 6
    COMMUTATION_AND_VELOCITY = 7


@unique
class SensorPorts(Enum):
    SENSOR_PORT_1 = 0
    SENSOR_PORT_2 = 1
    SENSOR_PORT_3 = 2
    SENSOR_PORT_4 = 3
    SENSOR_PORT_5 = 4


class ExceptionSensorConfig(Exception):
    pass


def get_motion_encoder_config_index(od, position_control=None, velocity_control=None) -> int:
    """Return the index of the encoder config used for:
    * Motion control (position_control=True, velocity_control=True)
    * Position or motion control (position_control=True)
    * Position control only (position_control=True, velocity_control=False)
    * Velocity or motion control (velocity_control=True)
    * Velocity control only (position_control=False, velocity_control=True)
    """

    if not position_control and not velocity_control:
        raise ExceptionSensorConfig("No function was selected.")

    if position_control == 1 and velocity_control == 0:
        selected_functions = [SensorFunctions.POSITION]
    elif position_control == 0 and velocity_control == 1:
        selected_functions = [SensorFunctions.COMMUTATION_AND_VELOCITY]
    else:
        selected_functions = [SensorFunctions.COMMUTATION_AND_MOTION_CONTROL_FEEDBACK,
                              SensorFunctions.MOTION_CONTROL_FEEDBACK_ONLY]
        if velocity_control is None:
            selected_functions.append(SensorFunctions.POSITION)
        if position_control is None:
            selected_functions.append(SensorFunctions.COMMUTATION_AND_VELOCITY)

    for subindex in range(0, od.feedback_sensor_ports_subindex()):
        sensor_config_index = od.feedback_sensor_ports(subindex + 1)
        if sensor_config_index != 0:
            # This implies there is a sensor configured. Get the configuration.
            sensor_function = od.parameter(sensor_config_index, 2)
            if sensor_function in [x.value for x in selected_functions]:
                return sensor_config_index

    raise ExceptionSensorConfig("No sensor is configured for any of the following functions: {}.".format(
        ', '.join([x.name for x in selected_functions])))


def get_commutation_encoder_config_index(od) -> int:
    """Return the index of the encoder config used for commutation."""

    for subindex in range(0, od.feedback_sensor_ports_subindex()):
        sensor_config_index = od.feedback_sensor_ports(subindex + 1)
        if sensor_config_index != 0:
            # This implies there is a sensor configured. Get the configuration.
            sensor_function = od.parameter(sensor_config_index, 2)
            if sensor_function in [SensorFunctions.COMMUTATION_AND_MOTION_CONTROL_FEEDBACK.value,
                                   SensorFunctions.COMMUTATION_AND_MONITORING.value,
                                   SensorFunctions.COMMUTATION_ONLY.value,
                                   SensorFunctions.COMMUTATION_AND_VELOCITY.value]:
                return sensor_config_index
    raise ExceptionSensorConfig("No sensor is configured for commutation.")


def get_sensor_function_for_position_control(od) -> int:
    """Gets the function of the configured sensor with position function

    Parameters
    ----------
    od

    Returns
    -------
        int
        sensor function

    """
    for subindex in range(0, od.feedback_sensor_ports_subindex()):
        sensor_config_index = od.feedback_sensor_ports(subindex + 1)
        if sensor_config_index != 0:
            sensor_function = od.parameter(sensor_config_index, 2)
            if sensor_function in [SensorFunctions.COMMUTATION_AND_MOTION_CONTROL_FEEDBACK.value,
                                   SensorFunctions.MOTION_CONTROL_FEEDBACK_ONLY.value,
                                   SensorFunctions.POSITION.value]:
                # It's used for position control!
                return sensor_function

    raise ExceptionSensorConfig("No sensor is configured for position control.")


def get_sensor_function_for_velocity_control(od) -> int:
    """Gets the function of the configured sensor with velocity function
    Parameters
    ----------
    od
    Returns
    -------
        int
        sensor function
    """
    for subindex in range(0, od.feedback_sensor_ports_subindex()):
        sensor_config_index = od.feedback_sensor_ports(subindex + 1)
        if sensor_config_index != 0:
            sensor_function = od.parameter(sensor_config_index, 2)
            if sensor_function in [SensorFunctions.COMMUTATION_AND_MOTION_CONTROL_FEEDBACK.value,
                                   SensorFunctions.MOTION_CONTROL_FEEDBACK_ONLY.value,
                                   SensorFunctions.COMMUTATION_AND_VELOCITY.value]:
                # It's used for velocity control!
                return sensor_function

    raise ExceptionSensorConfig("No sensor is configured for velocity control.")


def has_circulo_internal_sensors(od) -> bool:
    """
    Check whether the drive has circulo internal sensors.
    """
    circulo_with_internal_encoders = ['8502-01', '8502-02', '8503-01', '8503-02', '8504-01', '8504-02',
                                      '8505-01', '8505-02']
    return od.manufacturer_device_name() in circulo_with_internal_encoders


def get_enabled_circulo_internal_sensor_ports(od) -> List:
    """Get a list of sensor ports that have a circulo internal sensor enabled.

    Parameters
    ----------
    od

    Returns
    -------
    sensor_ports : List
        List of sensor ports

    """
    sensor_ports = []
    if has_circulo_internal_sensors(od):
        for sensor_port in [SensorPorts.SENSOR_PORT_1, SensorPorts.SENSOR_PORT_2]:
            sensor_config_index = od.feedback_sensor_ports(sensor_port.value + 1)
            if sensor_config_index != 0:
                # This implies there is a sensor configured. Get the configuration.
                sensor_function = od.parameter(sensor_config_index, 2)
                if sensor_function is not SensorFunctions.DISABLED.value:
                    sensor_ports.append(sensor_port)
    return sensor_ports


def get_si_unit_scaling_factor(od) -> int:
    """Calculates SI_unit_velocity factor based on the SI unit velocity prefix

    Parameters
    ----------
    od

    Returns
    -------
        int
        Velocity scaling factor based on the configured SI prefix

    """

    si_unit_velocity = od.si_unit_velocity()

    if si_unit_velocity == 11814656:
        return 1
    if si_unit_velocity == 4290004736:
        return 10
    if si_unit_velocity == 4273227520:
        return 100
    if si_unit_velocity == 4256450304:
        return 1000


def get_rpm_unit(od) -> str:
    """ Return the user defined unit of RPM (mili, centi, deci) according to velocity SI Unit
    Parameters
    ----------
    od
    Returns
    -------
        string
        RPM unit with SI prefix
    """

    si_unit_velocity = od.si_unit_velocity()

    if si_unit_velocity == 11814656:
        return 'rpm'
    if si_unit_velocity == 4290004736:
        return 'deci-rpm'
    if si_unit_velocity == 4273227520:
        return 'centi-rpm'
    if si_unit_velocity == 4256450304:
        return 'mili-rpm'


def get_gearbox_ratio(od):
    """ Calculate the gear ratio factor
    This is the factor between the motor shaft and the drive shaft.

    Returns
    -------
    int
        Gear ratio factor
    """

    gear_ratio = od.gear_ratio_motor_revolutions()  # Gear ratio: motor rev
    gear_ratio //= od.gear_ratio_shaft_revolutions()  # Gear ratio: shaft rev
    return gear_ratio


def get_gear_ratio(od):
    """ Calculate the gear ratio factor
    This is the factor between the motor shaft and the position control shaft.
    The function returns the gearbox ratio if the sensor with position function is not mounted on the
    motor shaft, or 1 otherwise.

    Returns
    -------
    int
        Ratio between motor shaft and position control
    """

    position_control_encoder_index = get_motion_encoder_config_index(od, position_control=True)
    commutation_encoder_index = get_commutation_encoder_config_index(od)
    if position_control_encoder_index != commutation_encoder_index:
        gear_ratio = get_gearbox_ratio(od)
    else:
        gear_ratio = 1
    return gear_ratio


def get_tachometer_ratio(od):
    """ Calculate the tachometer ratio factor
    This is the factor between the motor shaft and the velocity control shaft.
    The function returns the gearbox ratio if the sensor with velocity function is not mounted on the
    motor shaft, or 1 otherwise.

    Returns
    -------
    int
        Ratio between motor shaft and velocity control
    """

    velocity_control_encoder_index = get_motion_encoder_config_index(od, velocity_control=True)
    commutation_encoder_index = get_commutation_encoder_config_index(od)
    if velocity_control_encoder_index != commutation_encoder_index:
        tachometer_ratio = get_gearbox_ratio(od)
    else:
        tachometer_ratio = 1
    return tachometer_ratio


def set_current_position(od, sc, desired_position):
    """Set the current position to desired_position (with home offset)"""

    # Make sure motor is not turning
    timeout = time.time() + 5
    current_position = od.position_actual_value()
    while True:
        time.sleep(0.5000)
        if math.isclose(current_position, od.position_actual_value(), abs_tol=20):
            break
        else:
            if time.time() > timeout:
                pytest.fail("Motor is still turning ({} -> {} in the last 0.5 seconds).".format(
                    current_position, od.position_actual_value()))
            current_position = od.position_actual_value()

    # Set Home offset using current position and home offset
    home_offset = od.home_offset()

    old_current_position = od.position_actual_value()
    new_home_offset = home_offset - old_current_position + desired_position

    od.home_offset(value=new_home_offset)
    reload_drive_configuration(sc)

    # Check if the profiler is done
    timeout = time.time() + 2
    while True:
        current_position = od.position_actual_value()
        time.sleep(0.010)
        if math.isclose(current_position, desired_position, abs_tol=20):
            logging.debug("Home offset changed from {} to {}. The position actual value changed from {} to {}."
                         .format(home_offset, new_home_offset, old_current_position, desired_position))
            break

        if time.time() > timeout:
            pytest.fail("Position {} didn't change to {} when setting home offset. Current position is {}.".format(
                old_current_position, desired_position, current_position))


def remove_soc_timer_wraparound(time_array, diff_threshold=-30e3):
    """Remove the discontinuities in a timestamp derived from the SoC timer

    The SoC timer is running at 100 MHz and fills a 32-bit unsigned integer. Therefore, it will wrap around after
    `2**32/100 = 42949672.96 us`. Due to the way we round the timestamp in the Motion Drive firmware, this results
    in a time that never reaches 42949672.

    The way this works is:

    1. Take the numerical derivative (forward-difference).
    2. Identify abnormally large spikes, assumed to correspond to rollover.
    3. Subtract the max value from these spikes.
    4. Compute the integral (cumulative sum) of the repaired derivative.

    Parameters
    ----------
    time_array : np.Array()
        The Numpy array that contains the time series.
    diff_threshold : int, optional
        The value to start subtracting the max timer value for. Assuming your time diffs are normally very small, it's
        a good idea to set this to something very big (-30e3). Also, because the time is in an unsigned integer and
        always counts up, the discontinuities will always be a jump negative. That means this value should always be
        given negative.

    Returns
    -------
    time_array : np.Array()
        The resulting array with the discontinuities removed and the initial time zeroed.
    """
    # TODO: Might be nice to have the ability to start the time from the original start, rather than from zero?

    # Take the numerical derivative of the time.
    time_diff = np.diff(time_array)
    # Compute the time where an overflow will happen.
    max_time = int(2 ** 32 / 100) / 1e3
    # Find the spikes (where the diff is very big negative number).
    wrap_indices = np.where(time_diff <= diff_threshold)
    # Subtract out the expected max value for the time, for all discontinuities.
    # This intends to preserve the time-delta for the sample where the discontinuity happened.
    for index in wrap_indices:
        time_diff[index] += max_time
    # Take the cumulative sum (integral) to get back to the original time series.
    # Note that this starts from zero (removes the initial time offset). Add zero to the start to preserve length.
    time_data_repaired = np.cumsum(np.insert(time_diff, 0, 0))
    return time_data_repaired


def get_data_overflows(data, data_resolution, max_step_relative=0.1):
    """Check where are the overflows in the data and return the positions in the list where it happened.

    Parameters
    ----------
    data : List
        A list with the data to check.
    data_resolution : int
        Resolution of the data to check.
    max_step_relative : float, optional
        Maximum step that the position data can have, relative to the data resolution

    Returns
    -------
    positive_overflows : List
        A list with the position of the positive overflows.
    negative_overflows : List
        A list with the position of the negative overflows.
    """
    positive_overflows = []
    negative_overflows = []
    low_overflow_threshold = data_resolution * max_step_relative
    high_overflow_threshold = data_resolution * (1 - max_step_relative)
    for i in range(1, len(data)):
        if data[i - 1] > high_overflow_threshold and data[i] < low_overflow_threshold:
            positive_overflows.append(i)
        if data[i - 1] < low_overflow_threshold and data[i] > high_overflow_threshold:
            negative_overflows.append(i)
    return positive_overflows, negative_overflows


def remove_data_overflows(data, data_resolution, max_step_relative=0.1):
    """Remove all overflows from data to make it continuous.

    Parameters
    ----------
    data : List
        A list with the data to modify.
    data_resolution : int
        Resolution of the data to modify.
    max_step_relative : float, optional
        Maximum step that the position data can have, relative to the data resolution

    Returns
    -------
    continuous_data : List
        A list with the modified data.
    """
    positive_overflows, negative_overflows = get_data_overflows(data, data_resolution, max_step_relative)
    continuous_data = list(data)
    for position in positive_overflows:
        continuous_data[position:] = [x + data_resolution for x in continuous_data[position:]]
    for position in negative_overflows:
        continuous_data[position:] = [x - data_resolution for x in continuous_data[position:]]
    return continuous_data

