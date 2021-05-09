"""
SOMANET Profiler Helpers

Contains the helpers to use the position and velocity profilers.

Usage
----

It is recommended to use a standard way of importing:
    ``import somanet_profiler_helpers as sph``
"""

import time
import math
import pytest
import somanet_toolbox as stb
from enum import Enum, unique



@unique
class VelocityParametersFrame(Enum):
    """
    Enum with all possible frames.
    """
    MOTOR_SHAFT_FRAME = 0
    DRIVE_SHAFT_FRAME = 1
    VELOCITY_CONTROL_FRAME = 2
    POSITION_CONTROL_FRAME = 3

class TorqueProfileHandler:

    def __init__(self, sc, od):
        self.sc = sc
        self.od = od

        self.torque_slope = 0
        self.target_torque = 0
        self.target_tolerance = 0
        self.profiler_timeout = None
        self.stabilization_duration = None

    def set_profiler_configuration(self, 
                                   torque_slope, 
                                   target_tolerance,
                                   profiler_timeout = None,
                                   stabilization_duration = None):
        """Set the configuration for the profiler.

        Parameters
        ----------
        torque slope:int
            Profile slope in permils per rated torque
        Returns
        -------
            Nothing
        """
        self.torque_slope = torque_slope
        self.od.torque_slope(self.torque_slope)

        self.target_tolerance = target_tolerance

        if profiler_timeout is not None:
            self.profiler_timeout = profiler_timeout
        if stabilization_duration is not None:
            self.stabilization_duration = stabilization_duration
    
    def set_op_mode(self):
        """Sets the Profile torque op mode."""
        self.sc.set_op_mode(self.sc.OP_MODES.PROFILE_TORQUE)

    def enable_profiler(self):
        """Enable the torque profiler without setting any target."""
        self.sc.enable_operation()

    def set_target_torque(self, target_torque):
        """Set a target torque.

        Parameters
        ----------
        target_torque:int
            Target torque in permils per rated torque.
        Returns
        -------
            Nothing
        """
        self.target_torque = target_torque
        self.od.target_torque(self.target_torque)

    def is_target_reached(self):
        """Check if the target torque is achieved."""
        # Check if the profiler is done
        torque_demand = self.od.torque_demand()
        if math.isclose(torque_demand, self.target_torque,
                        abs_tol=int(self.target_tolerance)):
            if time.time() > self.stabilization_time:
                return True
        else:
            self.stabilization_time = time.time() + self.stabilization_duration
        return False

class VelocityProfileHandler:

    VELOCITY_PARAMETERS_FRAME = VelocityParametersFrame
    DEFAULT_PROFILER_TIMEOUT = 20
    DEFAULT_STABILIZATION_DURATION = 2

    def __init__(self, sc, od):
        self.sc = sc
        self.od = od

        self.si_unit_scaling_factor = stb.get_si_unit_scaling_factor(od)
        self.tachometer_ratio_factor = stb.get_tachometer_ratio(od)
        self.gear_ratio_factor = stb.get_gear_ratio(od)
        self.gearbox_ratio = stb.get_gearbox_ratio(od)

        # Profile acceleration/deceleration in RPM/s and in the velocity control frame
        self.acceleration = 0
        self.deceleration = 0

        # Target tolerance in RPM and in the velocity control frame
        self.target_tolerance = 0

        self.profiler_timeout = self.DEFAULT_PROFILER_TIMEOUT
        self.stabilization_duration = self.DEFAULT_STABILIZATION_DURATION
        self.stabilization_time = None

        # Target velocity in RPM and in the velocity control frame
        self.target_velocity = 0

        # Variable to select the configuration frame
        self.configured_frame = None
        self.configured_frame_to_velocity_control_frame = 0

    def set_profiler_configuration(self, velocity_parameters_frame, acceleration, deceleration, target_tolerance,
                                   profiler_timeout=None, stabilization_duration=None):
        """Set the configuration for the profiler.

        Parameters
        ----------
        velocity_parameters_frame:Enum
            Select in which frame are the velocity and acceleration parameters provided.
            E.g., if a target velocity of 100 rpm is set, this is what would happen if the frame configured is:
                - Motor shaft frame: the motor shaft will turn at 100 rpm, independently of where the encoders are.
                - Drive shaft frame: the drive shaft will turn at 100 rpm, independently of where the encoders are.
                - Velocity control frame: the shaft where the velocity control encoder is mounted will turn at 100 rpm.
                - Position control frame: the shaft where the position control encoder is mounted will turn at 100 rpm.
        acceleration:int or float
            Profile acceleration in RPM/s
        deceleration:int or float
            Profile deceleration in RPM/s
        target_tolerance: int or float
            Target tolerance in RPM
        profiler_timeout:float (Optional)
            Timeout for reaching the target in seconds.
        stabilization_duration:float (Optional)
            Duration in seconds that the velocity should be under the target tolerance once the target is reached.
        Returns
        -------
            Nothing
        """
        self.configured_frame = velocity_parameters_frame

        if self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.DRIVE_SHAFT_FRAME:
            # Factor to convert configured frame (drive shaft frame) to velocity control frame
            self.configured_frame_to_velocity_control_frame = self.gearbox_ratio / self.tachometer_ratio_factor
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.MOTOR_SHAFT_FRAME:
            # Factor to convert configured frame (motor shaft frame) to velocity control frame
            self.configured_frame_to_velocity_control_frame = 1 / self.tachometer_ratio_factor
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.VELOCITY_CONTROL_FRAME:
            # Factor to convert configured frame (velocity control frame) to velocity control frame
            self.configured_frame_to_velocity_control_frame = 1
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.POSITION_CONTROL_FRAME:
            # Factor to convert configured frame (position control frame) to velocity control frame
            self.configured_frame_to_velocity_control_frame = self.gear_ratio_factor / self.tachometer_ratio_factor

        # Convert the variables from configured frame to velocity control frame
        self.target_tolerance = target_tolerance * self.configured_frame_to_velocity_control_frame
        self.acceleration = acceleration * self.configured_frame_to_velocity_control_frame
        self.deceleration = deceleration * self.configured_frame_to_velocity_control_frame

        # Set the parameters once changed to the configured frame
        self.od.profile_acceleration(int(self.acceleration * self.si_unit_scaling_factor))
        self.od.profile_deceleration(int(self.deceleration * self.si_unit_scaling_factor))
        if profiler_timeout is not None:
            self.profiler_timeout = profiler_timeout
        if stabilization_duration is not None:
            self.stabilization_duration = stabilization_duration

        # Reset velocity to 0
        self.target_velocity = 0
        self.od.target_velocity(self.target_velocity)

    def set_op_mode(self):
        """Sets the Profile velocity op mode."""
        self.sc.set_op_mode(self.sc.OP_MODES.PROFILE_VELOCITY)

    def enable_profiler(self):
        """Enable the velocity profiler without setting any target."""
        self.sc.enable_operation()

    def set_target_velocity(self, target_velocity):
        """Set a target velocity.

        Parameters
        ----------
        target_velocity:int
            Target velocity in RPM. The frame for this variable is set in the method `set_profiler_configuration()`.
        Returns
        -------
            Nothing
        """
        # Convert target velocity to velocity control frame
        self.target_velocity = int(target_velocity * self.configured_frame_to_velocity_control_frame)
        self.od.target_velocity(self.target_velocity * self.si_unit_scaling_factor)

        # Initialize stabilization time
        self.stabilization_time = time.time() + self.stabilization_duration

    def is_target_reached(self):
        """Check if the target velocity is achieved."""
        # Check if the profiler is done
        velocity_demand_value = self.od.velocity_demand_value()
        if math.isclose(velocity_demand_value, self.target_velocity * self.si_unit_scaling_factor,
                        abs_tol=int(self.target_tolerance * self.si_unit_scaling_factor)):
            if time.time() > self.stabilization_time:
                return True
        else:
            self.stabilization_time = time.time() + self.stabilization_duration
        return False

    def go_to_velocity(self, target_velocity):
        """Go to target velocity and wait until it is achieved.

        Parameters
        ----------
        target_velocity:int
            Target velocity in RPM. The frame for this variable is set in the method `set_profiler_configuration()`.
        Returns
        -------
            Nothing
        """
        self.set_target_velocity(target_velocity)
        # Check if the profiler is done
        timeout = time.time() + self.profiler_timeout
        while True:
            time.sleep(0.010)
            if self.is_target_reached():
                return
            if time.time() > timeout:
                velocity_demand_value = self.od.velocity_demand_value()
                pytest.fail("Target velocity ({} RPM) wasn't achieved ({} RPM).".format(
                    self.target_velocity / self.configured_frame_to_velocity_control_frame,
                    (velocity_demand_value / self.si_unit_scaling_factor) /
                    self.configured_frame_to_velocity_control_frame))


class ProfilePositionHandler:
    """Handler to use the position profiler."""

    VELOCITY_PARAMETERS_FRAME = VelocityParametersFrame
    DEFAULT_TARGET_TOLERANCE = 30
    DEFAULT_PROFILER_TIMEOUT = 20
    DEFAULT_STABILIZATION_DURATION = 2

    def __init__(self, sc, od):
        self.sc = sc
        self.od = od

        self.si_unit_scaling_factor = stb.get_si_unit_scaling_factor(od)
        self.tachometer_ratio_factor = stb.get_tachometer_ratio(od)
        self.gear_ratio_factor = stb.get_gear_ratio(od)
        self.gearbox_ratio = stb.get_gearbox_ratio(od)

        # Profile acceleration/deceleration in RPM/s and in the position control frame
        self.acceleration = 0
        self.deceleration = 0

        # Profile velocity in RPM and in the position control frame
        self.max_velocity = 0

        self.target_tolerance = self.DEFAULT_TARGET_TOLERANCE
        self.profiler_timeout = self.DEFAULT_PROFILER_TIMEOUT
        self.stabilization_duration = self.DEFAULT_STABILIZATION_DURATION
        self.stabilization_time = None

        self.target_position = None

        # Variable to select the configuration frame
        self.configured_frame = None
        self.configured_frame_to_position_control_frame = 0

    def set_profiler_configuration(self, velocity_parameters_frame, acceleration, deceleration, max_velocity,
                                   target_tolerance=None, profiler_timeout=None, stabilization_duration=None):
        """Set the configuration for the profiler.

        Parameters
        ----------
        velocity_parameters_frame:Enum
            Select in which frame are the velocity and acceleration parameters provided.
            E.g., if a max velocity of 100 rpm is set, this is what would happen if the frame configured is:
                - Motor shaft frame: the motor shaft will turn at 100 rpm, independently of where the encoders are.
                - Drive shaft frame: the drive shaft will turn at 100 rpm, independently of where the encoders are.
                - Velocity control frame: the shaft where the velocity control encoder is mounted will turn at 100 rpm.
                - Position control frame: the shaft where the position control encoder is mounted will turn at 100 rpm.
        acceleration:int or float
            Profile acceleration in RPM/s
        deceleration:int or float
            Profile deceleration in RPM/s
        max_velocity:int or float
            Profile velocity in RPM
        target_tolerance: int or float
            Target tolerance in ticks
        profiler_timeout:float (Optional)
            Timeout for reaching the target in seconds.
        stabilization_duration:float (Optional)
            Duration in seconds that the position should be under the target tolerance once the target is reached.
        Returns
        -------
            Nothing
        """
        self.configured_frame = velocity_parameters_frame

        if self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.DRIVE_SHAFT_FRAME:
            # Factor to convert configured frame (drive shaft frame) to position control frame
            self.configured_frame_to_position_control_frame = self.gearbox_ratio / self.gear_ratio_factor
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.MOTOR_SHAFT_FRAME:
            # Factor to convert configured frame (motor shaft frame) to position control frame
            self.configured_frame_to_position_control_frame = 1 / self.gear_ratio_factor
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.POSITION_CONTROL_FRAME:
            # Factor to convert configured frame (position control frame) to position control frame
            self.configured_frame_to_position_control_frame = 1
        elif self.configured_frame is self.VELOCITY_PARAMETERS_FRAME.VELOCITY_CONTROL_FRAME:
            # Factor to convert configured frame (velocity control frame) to position control frame
            self.configured_frame_to_position_control_frame = self.tachometer_ratio_factor / self.gear_ratio_factor

        # Convert the variables from configured frame to position control frame
        self.acceleration = acceleration * self.configured_frame_to_position_control_frame
        self.deceleration = deceleration * self.configured_frame_to_position_control_frame
        self.max_velocity = max_velocity * self.configured_frame_to_position_control_frame

        # Set the parameters once changed to the configured frame
        self.od.profile_acceleration(int(self.acceleration * self.si_unit_scaling_factor))
        self.od.profile_deceleration(int(self.deceleration * self.si_unit_scaling_factor))
        self.od.profile_velocity(int(self.max_velocity * self.si_unit_scaling_factor))
        if target_tolerance is not None:
            self.target_tolerance = target_tolerance
        if profiler_timeout is not None:
            self.profiler_timeout = profiler_timeout
        if stabilization_duration is not None:
            self.stabilization_duration = stabilization_duration

    def set_op_mode(self):
        """Sets the Profile position op mode."""
        self.sc.set_op_mode(self.sc.OP_MODES.PROFILE_POSITION)

    def enable_profiler(self):
        """Enable the position profiler without setting any target."""
        self.sc.enable_operation()

    def start_trajectory(self, target_position):
        """Start a position profiler trajectory.

        Parameters
        ----------
        target_position:int
            Target position in encoder ticks.
        Returns
        -------
            Nothing
        """

        # Save and set target position
        self.target_position = target_position

        # Tell the profiler to execute the latest target.
        self.od.target_position(target_position)
        self.sc.pp_start_next_position_now()

        # Pause very quickly to give the profiler a chance to reset the demand value.
        time.sleep(0.010)

        self.sc.pp_reset_bits()

        # Initialize stabilization time
        self.stabilization_time = time.time() + self.stabilization_duration

    def is_target_reached(self, expected_position=None):
        """Check if the target position is achieved,

        Parameters
        ----------
        expected_position:int (Optional)
            Expected position in encoder ticks.
            If this value is not provided, target position will be taken as expected position.
        Returns
        -------
            Nothing
        """

        if self.target_position is None:
            pytest.fail("In order to check if the target is reached, a trajectory has to be started.")

        if expected_position is None:
            expected_position_internal = self.target_position
        else:
            expected_position_internal = expected_position

        # Check if the profiler is done
        demand_position_internal = self.od.position_demand_internal_value()
        if math.isclose(demand_position_internal, expected_position_internal, abs_tol=self.target_tolerance):
            if time.time() > self.stabilization_time:
                return True
        else:
            self.stabilization_time = time.time() + self.stabilization_duration
        return False

    def go_to_position(self, target_position, expected_position=None):
        """Go to target position and wait until it is achieved.

        Parameters
        ----------
        target_position:int
            Target position in encoder ticks.
        expected_position:int (Optional)
            Expected position in encoder ticks.
            If this value is not provided, target position will be taken as expected position.
        Returns
        -------
            Nothing
        """
        self.start_trajectory(target_position)
        # Check if the profiler is done
        timeout = time.time() + self.profiler_timeout
        while True:
            time.sleep(0.010)
            if self.is_target_reached(expected_position):
                return
            if time.time() > timeout:
                demand_position_internal = self.od.position_demand_internal_value()
                pytest.fail("Expected position ({}) wasn't achieved ({}) when setting target position ({}).".format(
                    expected_position, demand_position_internal, self.target_position))
