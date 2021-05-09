# CI Test Suite for app_motion_drive

This contains the test and configuration for the Synapticon CI Farm. It's
set up for execution on the CI Farm, but can be run manually.

## How to run manually

### Setup your environment

To setup your environment to execute these tests, we recommend the following:

* Install python3 with `apt install python3` if it's not already installed.
* Create a virtual environment (venv) with python3 (put it anywhere, but `~/venv/` is nice):
  `python3 -m venv ~/venv/app_motion_drive_test`
* Activate the venv: `source ~/venv/app_motion_drive_test/bin/activate`. Note that you will need to do this in every
  console that you want to use this environment! From now on, all commands noted here will require that you have
  activated your venv. Your command prompt should change to look like this: `(app_motion_drive_test) $`
* Install all the python dependencies we need:
    * `pip install pytest wheel motion-master-bindings numpy matplotlib ea-psu-controller`
    * If you run a test and it complains about a missing package, `pip install <that-package>`

That's it. If you get an error when running the pytest command below, the mostly likely cause is pytest isn't working
with python3. Instead of `pytest`, you can use `python3 -m pytest`. But it's recommended to fix your venv so that the
standard commands work.

### Run the tests

Assuming one has activated the proper virtual environment, you can run a test
(or a matching set of tests) on your OBLAC Box with:

    $ pytest -k basic_motion_control --address oblac-drives-235fwdf.local

Explanation and further handy options:

* `-k <string>` run tests that match the `<string>`
* `-vl` be verbose (`v`) and show local variables in traceback (`l`)
* `-rxX` show extra test summary (`r`) for expected-failed (`x`) and expected-passed (`X`)
* `--log-cli-level=DEBUG` print all debug-level logs to the terminal (INFO is good too)
* `--tb=short` keep the exception traceback short and sweet
* `--generate_doc=true` generates atr summary at `/doc/atr/index.rst`
* `--flash_fw` flash the firmware on all nodes connected in chain (test run order set to 1)
* `--control_psu` turn ON power supply at the beginning and turn OFF at the end of test execution (on CI setup only)
* `--inc` to run the pytest on a single or multiple devices at a specific position within a chain (positions start from 0 as can be seen from Oblac GUI)
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --inc 2`
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --inc 1,2,4`
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --inc 1-4`
* `--exc` to skip the pytest on a single or multiple devices at specific position within a chain and run on all other devices
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --exc 2`
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --exc 1,2,4`
  - `$ pytest -k basic_motion_control --address oblac-drives-235fwdf.local --exc 3`


You can read a lot more about pytest options on the Interweb.

## Guidelines for writing tests

### For code that is not a test

* MUST be documented with [Numpy docstring guidelines](https://numpydoc.readthedocs.io/en/latest/format.html). This is to improve clarity for the inputs and output types.
* MUST include type hints for all inputs and outputs. Again, to catch errors and improve clarity before shipping.

### Test cases

* Document each test case according to the ATP guidelines. This will be used to generate the ATP automatically.

## Directory list explanation

The following directory structure is used for the CI robots.

```
pytest/
    robot_name/ - the name of the robot under which these tests will run
        data/   - any data that the robot needs for configuration
        test/   - the tests that should be executed on this robot
```

Under all robot directories is a `README.md` file that explains what the robot does and any
special things it can do (like if it has a DAQ, for example).

Example:

```
pytest/
    robot_axis_chain/
        README.md
        data/
            axis0/config.csv, .hardware_description
            axis1/config.csv, .hardware_description
            axis2/config.csv, .hardware_description
            axis3/config.csv, .hardware_description
        test/
            test_basic_motion_control.py
    robot_io_with_daq/
        README.md
        data/
            axis0/config.csv, .hardware_description
            axis1/config.csv, .hardware_description
        test/
            test_digital_io.py
```
