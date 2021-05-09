# Robot: Axis Chain

This robot contains a single EtherCAT network with a bunch of simple
axes. These axes are composed of:

1. A SOMANET Servo Node
2. A BLDC motor paired appropriately to the Servo Node
3. At least one encoder on the motor shaft for commutation
4. [optional] A second encoder used for position and/or motion control
5. [optional] A static load (uncontrolled) such as a spring, mass, and/or damper

This robot provides the base for testing lots of different axis configurations.

## Requirements

All axes in the chain must be pre-configured to properly drive a motor without
further configuration effort. The tests that run here assume that the object
dictionary contains the optimal or near-optimal values for the axis.

Tests executed on this chain may choose to execute the same actions on all
axes, so all axes should be able to execute all the basic functionality for 
motion control.
