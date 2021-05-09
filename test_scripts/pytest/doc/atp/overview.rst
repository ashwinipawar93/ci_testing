========
Overview
========

This document is the ATP for the SOMANET software.
The acceptance test verifies that the system works as required and validates
that the correct functionality has been delivered. The ATP establishes the
acceptance test framework used by the acceptance test team to plan, execute,
and document acceptance testing. It describes the scope of the work performed
and the approach taken to execute the tests created to validate that the
system performs as required. The details of the ATP are developed according
to the requirements specifications, and must show traceability back to those
specifications.


Acceptance test approach
------------------------

Tests are grouped by scenarios, they run in parallel on different robots.
Each robot is defined by the nodes (SOMANET boards) and devices (motors, data
acquisition devices) attached to it.

The scenarios can be found in the :ref:`scenarios` link:

Acceptance test process
-----------------------

Each scenarios has 3 main stages: setup, execution and teardown:

1. **Setup**: a list of functions, ran first. If these are all non-terminal, the test execution starts. Example: Turn on power supplies and ensure devices are connected
2. **Execution**: a list of functions, run after the setup (only if the setup is successful) as long as those are non-terminal.

3. **Teardown**: a list of functions, guaranteed to run after the main functions. If any are terminal, other teardown functions will continue to be run. Example: Turn off the power supply.  
   
-------------
What is in scope, what is out
