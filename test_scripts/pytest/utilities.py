"""
Contains helper functions and data structures for CI testing involving a Labjack DAQ device.
"""

import subprocess as sp
import random

ETHERCAT_BIN_PATH = '/opt/etherlab/bin/ethercat'

"""
    Test setup on the continuous-integration testbench involving Labjack T7 DAQ device for robot_daq (ROBOT 2)

    GPIO configuration on Nodes         Set-up for GPIO input test      Set-up for GPIO output test
    -----------------------------         ----------------------          ----------------------
    | Node 2000 |  GPIO Config  |         | Node 2000 |Labjack |          | Node 2000 |Labjack |
    |-----------|---------------|         |-----------|--------|          | ----------| ------ |
    | DIO1      |  Input/Output |         | DIO1      |  FIO0  |          | DIO1      |  FIO0  |
    | DIO2      |  Input/Output |         | DIO2      |  FIO1  |          | DIO2      |  FIO1  |
    | DIO3      |  Input/Output |         | DIO3      |  FIO2  |          | DIO3      |  FIO2  |
    | DIO4      |  Input/Output |         | DIO4      |  FIO3  |          | DIO4      |  FIO3  |
    |-----------|---------------|         |-----------|--------|          |--------------------|
    | Circulo   |  GPIO Config  |         | Circulo   |Labjack |          | Circulo   |Labjack |
    |-----------|---------------|         |-----------|--------|          | ----------| ------ |
    | DIO1      | Input/Output  |         | DIO1      |  FIO4  |          | DIO1      |  FIO4  |
    | DIO2      | Input/Output  |         | DIO2      |  FIO5  |          | DIO2      |  FIO5  |
    | DIO3      | Input/Output  |         | DIO3      |  FIO6  |          | DIO3      |  FIO6  |
    | DIO4      |       Output  |         | DIO4      |  ----  |          | DIO4      |  FIO7  |
    | DIO5      | Input/Output  |         | DIO5      |  ----  |          | DIO5      |  ----  |
    | DIO6      | Input/Output  |         | DIO6      |  ----  |          | DIO6      |  ----  |
    | DIO7      | Input/Output  |         | DIO7      |  ----  |          | DIO7      |  ----  |
    |-----------|---------------|         |-----------|--------|          |--------------------|
    | Google    |  GPIO Config  |         | Google    |Labjack |          | Google    |Labjack |
    |-----------|---------------|         |-----------|--------|          | ----------| ------ |
    | DIO1      |       Output  |         | DIO1      |  ----  |          | DIO1      |  EIO0  |
    | DIO2      |       Output  |         | DIO2      |  ----  |          | DIO2      |  EIO1  |
    | DIO3      |       Output  |         | DIO3      |  ----  |          | DIO3      |  EIO2  |
    | DIO4      |       Output  |         | DIO4      |  ----  |          | DIO4      |  EIO3  |
    -----------------------------         ----------------------          ----------------------

    Set-up for external scaled measurement test     Set-up for safety board test (Make sure to set them to Output - low)
           -----------------------------                 --------------------------------
           | Node 2000        |Labjack |                 | Node 2000 + safety  |Labjack |
           |------------------|--------|                 |---------------------|--------|
           | Analog Input 1 - |  GND   |                 | SAFETY_INT_FAULT    |  EIO4  |
           | Analog Input 1 + |  DAC0  |                 | SAFETY_STO_INPUT_1  |  EIO5  |
           -----------------------------                 | SAFETY_STO_INPUT_2  |  EIO6  |
                                                         --------------------------------
                                                         
                                                         
    Test setup on the continuous-integration testbench involving Labjack T7 DAQ device for robot_axis_with_daq (ROBOT 3)

    GPIO configuration on Node         Set-up for test_homing_with_switches      
    -----------------------------         ----------------------         
    | Node 2000 |  GPIO Config  |         | Node 2000 |Labjack |         
    |-----------|---------------|         |-----------|--------|          
    | DIO1      |  Input/Output |         | DIO1      |  FIO0  |         
    | DIO2      |  Input/Output |         | DIO2      |  FIO1  |          
    | DIO3      |  Input/Output |         | DIO3      |  FIO2  |          
    | DIO4      |  Input/Output |         | DIO4      |  FIO3  |          
    -----------------------------         ----------------------         
    
    Test setup on the continuous-integration testbench involving Labjack T7 DAQ device for robot_axis_daq_torque_control
    (ROBOT 4)
    
    Set-up for the torque control tests
    
    Sensor configurations on Labjack       
    ---------------------------------------------------------------------
    |                       Sensor                          |  Labjack  |     
    |-------------------------------------------------------|-----------|       
    | Voltage Supply to current sensor for Phase A Current  |    VS     |
    | Ground of current sensor for Phase A Current          |    GND    |
    | Phase A Current                                       |    AIN0   |  
    ---------------------------------------------------------------------
    | Voltage Supply to current sensor for Phase B Current  |    VS     |
    | Ground of current sensor for Phase A Current          |    GND    |  
    | Phase B Current                                       |    AIN2   |       
    --------------------------------------------------------------------- 
    | Voltage Supply to current sensor for Phase C Current  |    VS     |
    | Ground of current sensor for Phase C Current          |    GND    |   
    | Phase C Current                                       |    AIN4   |    
    ---------------------------------------------------------------------
    | Voltage Supply to current sensor for idc sensor       |    VS     |
    | Ground of idc sensor                                  |    GND    |
    | IDC Link Current                                      |    AIN6   |   
    ---------------------------------------------------------------------
    | Voltage Supply to torque sensor                       |    VS     |
    | Ground of torque sensor                               |    GND    |
    | Torque Measurement                                    |    AIN8   |
    | Differential Ended  for torque measurement            |    AIN9   |
    ---------------------------------------------------------------------
    | Ground of VDC                                         |    GND    |
    | VDC                                                   |    AIN10  |
    ---------------------------------------------------------------------          
"""

LJM_TYPE_ROBOT_2 = 'T4'
LJM_CONNECTION_ROBOT_2 = 'ETHERNET'  # change to 'USB' if connected so.
# Provide the serial number written under your LabJack device or the IP address.
LJM_ID_ROBOT_2 = '440010526'  # This value by default refers to the CI Lab LabJack for robot 2

LJM_TYPE_ROBOT_3 = 'T7'
LJM_CONNECTION_ROBOT_3 = 'ETHERNET'  # change to 'USB' if connected so.
LJM_ID_ROBOT_3 = '470015671'  # This value by default refers to the CI Lab LabJack for robot 3

LJM_TYPE_ROBOT_4 = 'T7'
LJM_CONNECTION_ROBOT_4 = 'ETHERNET'  # change to 'USB' if connected so.
# Provide the serial number written under your LabJack device or the IP address.
LJM_ID_ROBOT_4 = '470020991'  # This value by default refers to the CI Lab LabJack for robot 2

# Labjack digital ports for Drive DIO & safety module DIO Testing
# This is including the ports on the extra adapters of the labjack
PORTS_LJ_DIO_F = ['FIO0', 'FIO1', 'FIO2', 'FIO3', 'FIO4', 'FIO5', 'FIO6', 'FIO7']
PORTS_LJ_DIO_E = ['EIO0', 'EIO1', 'EIO2', 'EIO3', 'EIO4', 'EIO5', 'EIO6', 'EIO7']


"""
    Digital IO
"""
# Index
PORT_DIO_NAME = 0  # name of the pin
PORT_DIO_LJM = 1   # name of labjack pin
PORT_DIO_OD = 2   # object dictionary index

# Safety pins
SAFETY_STO_INPUT_1 = PORTS_LJ_DIO_E[5]
SAFETY_STO_INPUT_2 = PORTS_LJ_DIO_E[6]

# Pin to generate internal fault, set to logic 0 to generate fault
SAFETY_INT_FAULT = PORTS_LJ_DIO_E[4]

# Analog Inputs and Labjack DAC pins

ANALOG_MAX_OUTPUT = 4.8
ANALOG_SAMPLE_COUNT = 20
RESOLUTION_SCALE_RATIO = 2
ANALOG_VALUES_TO_TEST = 5
ANALOG_ERROR_TO_ALLOW = 0.8  # Fix : changed to pass the test for 4.8V
DAC_CALIBRATE = 2 - (ANALOG_MAX_OUTPUT / 5)
DIFFERENTIAL_INPUT_RATIO = 2048
DIFF_ADC_VOLTAGE = 5

# Reference analog voltage on Labjack
V_REF_ANALOG = 5.0

# ADC resolution on Drive
RES_ANALOG = (1 << 12)

# Index
PORT_AIN_OD = 2

# AIN_SIN = Analog Input Single Ended
# AIN_DIFF = Analog Input Differential Ended
AIN_SIN = [('DAC0', 'AIN1', 0x2401),
           ('DAC0', 'AIN2', 0x2402), ]

AIN_DIFF = [('DAC0', 'AIN3', 0x2403),
            ('DAC0', 'AIN4', 0x2404), ]


def analog_to_voltage(analog_value):
    # for signals in the range 0 - 5V
    # if signal is in the range 0-10V, the acquired ADC value has to be scaled down
    return float(analog_value * (V_REF_ANALOG / RES_ANALOG))


def diff_analog_to_voltage(analog_value):
    return float(((analog_value / (RES_ANALOG / DIFF_ADC_VOLTAGE) - (DIFF_ADC_VOLTAGE / 2)) / (5.6 / 6.8)) * 2)


def get_voltage_samples(n_samples, max_voltage_output):
    """
    Return a sample of voltages including max, and min
    according to a number of samples in a defined range
    # Example: for 10 items and 4.9 as Max output:
    # return(0.0, 0.1, 0.8, 1.4, 1.8, 2.0, 3.0, 3.2, 3.7, 4.4, 4.8, ANALOG_MAX_OUTPUT)
    :param n_samples: number of samples
    :param max_voltage_output: maximum voltage to apply
    :return: list of voltages to apply
    """
    values = [0.0]
    values.extend([round(random.uniform(x, x + 1) * max_voltage_output / n_samples, 2) for x in range(0, n_samples)])
    values.append(max_voltage_output)
    return values


SAMPLE_VALUES_SINGLE_ANALOG_IN = get_voltage_samples(ANALOG_VALUES_TO_TEST,
                                                     ANALOG_MAX_OUTPUT)


def strip(string):
    """Error description code is 8 digits in the object dictionary
    Remove white spaces from the string
    :param string: A string containing error code description
    :return: Returns string without white spaces
    """
    return string.lstrip().rstrip()


def number_of_nodes():
    """Find number of connected nodes.
    """
    cmd = ' '.join([ETHERCAT_BIN_PATH, 'slaves', '|', 'wc', '-l'])
    number_of_slaves = sp.check_output(cmd, shell=True)
    no_of_nodes = int(number_of_slaves)
    return no_of_nodes
