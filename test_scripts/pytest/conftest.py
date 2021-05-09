"""
Pytest Config File

Contains the fixtures used for individual tests.
"""
import pytest
from doc.summary import Summary
import os
import logging
import json
import re
# TODO: This maybe needs to be absorbed into a package (maybe bindings, maybe somanet_test_suite)
from motion_master_wrapper import MotionMasterWrapper
import somanet_od as sod
import somanet_cia402_state_control as sst
import ea_psu_controller as ea
import utilities as ut
import time

logger = logging.getLogger(__name__)
currentdir = os.path.dirname(os.path.realpath(__file__))
test_case_results = dict()


def pytest_addoption(parser):
    parser.addoption("--address", action="store", default='localhost',
                     help="connection to the Motion Master")
    parser.addoption("--inc", action="store",
                     help='Run test on specific device')
    parser.addoption("--exc", action="store",
                     help='Skip test on specific device')
    parser.addoption("--generate_doc", action="store",
                     help="generate ATP and ATR documentation")
    parser.addoption("--flash_fw", action="store_true",
                     help="Flash firmware")
    parser.addoption("--control_psu", action="store_true",
                     help="Remote control Power Supply")


@pytest.fixture(scope="session", autouse=True)
def psu(request):
    """Start the Power supply at beginning and stop at end of test execution.
    Exit if psu control is not requested.
    """

    if request.config.getoption("--control_psu"):
        logger.info("Turning ON power supply")
        _psu48 = ea.PsuEA(comport='ea-ps-48v')
        _psu48.remote_on()
        _psu48.output_on()
        # Wait till ethercat shows up
        time.sleep(3)
        # Wait for Motion Master's node identification
        # Motion master takes 8 seconds to identify single node after power cycle
        time.sleep(ut.number_of_nodes() * 8)

    yield

    if request.config.getoption("--control_psu"):
        logger.info("Turning OFF power supply")
        _psu48.output_off()
        _psu48.remote_off()


@pytest.fixture(scope="session")
def skip_flash_firmware(request):
    if not request.config.getoption("--flash_fw"):
        pytest.skip("Skip flashing firmware")


@pytest.fixture(scope='session')
def mmw(request):
    """Provide a Motion Master Wrapper"""
    # Attempt to connect to the Motion Master and initialize everything.
    mmw = MotionMasterWrapper(request.config.getoption("--address"), 1.0)
    try:
        mmw.connect_to_motion_master()
        # Gather device and parameter info for address and type checking.
        mmw.initialize_device_parameter_info_dict()
    except Exception as e:
        mmw.disconnect()
        raise e

    yield mmw
    # Shut down the wrapper properly after the session.
    mmw.disconnect()


@pytest.fixture(scope='session')
def device_list(request, mmw):
    """Provide the complete list of devices or the specific device if mentioned in command line
     at the start of the session.
     Device list is initially created from parsing data from mmw. However, this created device list
     does not contain devices in order (e.g 0,2,1) therefore while selecting specific device/devices
     for running test, we need to address them through their actual position and not through the
     order of devices in device list.
     """

    if request.config.getoption("--inc") is not None:
        _device_list = list(mmw.device_and_parameter_info_dict.values())
        _device_list_actual_position_index = []

        for device in _device_list:
            _device_list_actual_position_index.append(device['info'].position)

        assert _device_list, "Device list is empty"
        match1 = re.search(r'(,)', request.config.getoption("--inc"))
        match2 = re.search(r'(-)', request.config.getoption("--inc"))

        # For --inc 1,2,4
        if match1 is not None:
            number_of_nodes = re.split(r'\,', request.config.getoption("--inc"))
            number_of_nodes = list(map(int, number_of_nodes))

            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            index_list = []
            for index_1, item_1 in enumerate(number_of_nodes):
                for index_2, item_2 in enumerate(_device_list_actual_position_index):
                    if item_1 == item_2:
                        index_list.append(index_2)

            number_of_nodes = index_list
            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            modified_device_list = []
            for i in number_of_nodes:
                modified_device_list.append(_device_list[i])
            _device_list = modified_device_list

        # For --inc 1-3
        elif match2 is not None:
            number_of_nodes = re.split(r'\-', request.config.getoption("--inc"))
            number_of_nodes = list(map(int, number_of_nodes))

            number_of_nodes_extended = []
            last_node = number_of_nodes[1] + 1
            while number_of_nodes[0] < last_node:
                number_of_nodes_extended.append(number_of_nodes[0])
                number_of_nodes[0] += 1
            number_of_nodes = number_of_nodes_extended

            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            index_list = []
            for index_1, item_1 in enumerate(number_of_nodes):
                for index_2, item_2 in enumerate(_device_list_actual_position_index):
                    if item_1 == item_2:
                        index_list.append(index_2)

            number_of_nodes = index_list
            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            modified_device_list = []
            for i in number_of_nodes:
                modified_device_list.append(_device_list[i])
            _device_list = modified_device_list

        # For --inc 1
        else:
            assert _device_list, "Device list is empty"
            desired_position = request.config.getoption("--inc")
            desired_position = int(desired_position)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            list_of_nodes = []
            for node in _device_list:
                node_position = node['info'].position
                if node_position == desired_position:
                    list_of_nodes.append(node)
            _device_list = list_of_nodes

    elif request.config.getoption("--exc") is not None:
        _device_list = list(mmw.device_and_parameter_info_dict.values())
        _device_list_actual_position_index = []
        for device in _device_list:
            _device_list_actual_position_index.append(device['info'].position)

        assert _device_list, "Device list is empty"
        match1 = re.search(r'(,)', request.config.getoption("--exc"))
        match2 = re.search(r'(-)', request.config.getoption("--exc"))
        # For --exc 1,2,4
        if match1 is not None:
            number_of_nodes = re.split(r'\,', request.config.getoption("--exc"))
            number_of_nodes = list(map(int, number_of_nodes))

            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            index_list = []
            for index_1, item_1 in enumerate(number_of_nodes):
                for index_2, item_2 in enumerate(_device_list_actual_position_index):
                    if item_1 == item_2:
                        index_list.append(index_2)

            number_of_nodes = index_list
            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            excluded_device_list = []
            for i in number_of_nodes:
                excluded_device_list.append(_device_list[i])

            total_number_of_nodes = []
            for i in range(len(_device_list)):
                total_number_of_nodes.append(i)
            number_of_nodes = list(set(total_number_of_nodes).difference(number_of_nodes))

            included_device_list = []
            for i in number_of_nodes:
                included_device_list.append(_device_list[i])
            _device_list = included_device_list

        # For --exc 1-3
        elif match2 is not None:
            number_of_nodes = re.split(r'\-', request.config.getoption("--exc"))
            number_of_nodes = list(map(int, number_of_nodes))
            number_of_nodes_extended = []
            last_node = number_of_nodes[1] + 1
            while number_of_nodes[0] < last_node:
                number_of_nodes_extended.append(number_of_nodes[0])
                number_of_nodes[0] += 1
            number_of_nodes = number_of_nodes_extended

            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            index_list = []
            for index_1, item_1 in enumerate(number_of_nodes):
                for index_2, item_2 in enumerate(_device_list_actual_position_index):
                    if item_1 == item_2:
                        index_list.append(index_2)

            number_of_nodes = index_list
            desired_position = max(number_of_nodes)
            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            excluded_device_list = []
            for i in number_of_nodes:
                excluded_device_list.append(_device_list[i])

            total_number_of_nodes = []
            for i in range(len(_device_list)):
                total_number_of_nodes.append(i)
            number_of_nodes = list(set(total_number_of_nodes).difference(number_of_nodes))

            included_device_list = []
            for i in number_of_nodes:
                included_device_list.append(_device_list[i])
            _device_list = included_device_list

        # For --exc 1
        else:
            assert _device_list, "Device list is empty"
            desired_position = request.config.getoption("--exc")
            desired_position = int(desired_position)
            total_number_of_nodes = []
            for i in range(len(_device_list)):
                total_number_of_nodes.append(i)

            assert desired_position <= len(_device_list) - 1, "The desired position is out of range for the " \
                                                              "connected devices. Please specify a position within " \
                                                              "the range 0 - {}" .format(len(_device_list) - 1)

            desired_position = [desired_position]
            index_list = []
            for index_1, item_1 in enumerate(desired_position):
                for index_2, item_2 in enumerate(_device_list_actual_position_index):
                    if item_1 == item_2:
                        index_list.append(index_2)

            desired_position = index_list
            number_of_nodes = list(set(total_number_of_nodes).difference(desired_position))

            modified_device_list = []
            for i in number_of_nodes:
                modified_device_list.append(_device_list[i])
            _device_list = modified_device_list

    else:
        _device_list = list(mmw.device_and_parameter_info_dict.values())

    assert _device_list, "Device list is empty"

    for device in _device_list:
        device_address = device['info'].device_address
        device['object_dictionary'] = sod.ObjectDictionary(mmw, device_address)
        device['state_control'] = sst.StateControl(mmw, device_address)

        # Get the hardware description data from each node too.
        try:
            hardware_description_data = mmw.get_device_file(device_address, '.hardware_description')
            hardware_description = json.loads(hardware_description_data)
            device['hardware_description'] = hardware_description
        except Exception as e:
            logger.warning("Error retrieving .hardware_description: {}".format(e))
            # If this fails, just ignore it and make the data empty.
            device['hardware_description'] = {}

    return _device_list


@pytest.fixture(scope="function", autouse=True)
def clear_fault(device_list):
    for device in device_list:
        device_name = device['hardware_description']['device']['name']
        match = re.search(r'(Safety)', device_name)
        if match:
            return
        device['state_control'].fault_reset()


@pytest.fixture(scope='function', autouse=True)
def skip_if_no_devices(device_list):
    """Skip the test if there are no devices"""
    if len(device_list) < 1:
        pytest.skip("Need at least one device on the network.")


@pytest.fixture(scope='session')
def test_result_summary(request):
    """Creates summary file(.rst) of test results"""
    global test_case_results
    _summary = Summary()
    yield _summary

    # Exit if documentation is not requested
    if request.config.getoption("--generate_doc") is None:
        return

    for fname, res in test_case_results.items():
        _summary.save_test_results(fname, res)
    _rst = _summary.serialize_test_record()
    _path = os.path.join(currentdir, "doc/atr/index.rst")
    with open(_path, 'w') as f:
        f.write(_rst)
    test_case_results = dict()


@pytest.fixture(scope="function", autouse=True)
def collect_test_pydoc(request, test_result_summary):
    """Collect test requirements from test scripts after every single test case."""
    # Exit if documentation is not requested
    if request.config.getoption("--generate_doc") is None:
        return

    doc = request.function.__doc__
    fname = request.function.__name__
    test_result_summary.save_test_requirements(fname, doc)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Get the result of each test case in test script

    Details on how this works can be found here:
        https://doc.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    """
    global test_case_results
    outcome = yield

    result = outcome.get_result()
    if result.when == 'call':
        test_case_results[item.name] = result
        setattr(item, "rep_call", result)
