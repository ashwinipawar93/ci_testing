..    include:: <isopub.txt>

=========
Scenarios
=========

Different scenarios are started on each robot.
They depend on hardware that is attached to them.

Pytest Fixtures
-----------------
They are used to initialize test functions. They make sure that preconditions are satisfied. 

* _address : The address passed to the Motion Master Wrapper
* mmw : Provide a Motion Master Wrapper
* device_list : Provide the list of devices returned at the start of the session
* skip_if_no_devices : Skip the test if there are no devices  
* lookup : Retrieve some useful data before the tests start, to configure the tests

Motor Tests
---------------------
These are ran on scenarios with motor control application

.. autoclass:: test_motion_master.TestInternalSensors
   :members:

.. autoclass:: test_commutation_offset_detection.TestCommutationOffsetDetection
   :members:

.. autoclass:: test_object_dictionary_sanity.TestInternalSensors
   :members:

.. autoclass:: test_object_dictionary_sanity.TestFirmwareMetadata
   :members:

.. autoclass:: test_profile_position.TestProfilePosition
   :members: test_profile_position_software_limit_1, test_profile_position_trajectory

.. autoclass:: test_cogging_torque_recording.TestCoggingTorqueRecording
   :members:

.. autoclass:: test_filesystem.TestFilesystem
   :members:

.. autoclass:: test_homing.TestHoming
   :members:

.. autoclass:: test_profile_velocity.TestProfileVelocity
   :members:
