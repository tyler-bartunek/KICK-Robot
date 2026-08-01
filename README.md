
# The KICK Robot <img src="images/Updated_KICK_logo.png" alt="KICK Logo" width="550" align = "right"/>

&nbsp;
&nbsp;
_Democratizing robotics, one shoebox at a time_

The KICK (Kinematically Interchangeable Control Kit) Robot framework is an open-source platform designed to make learning about and development of mobile robotic systems accessible, modular, and affordable.

## Table of Contents
- [Repository Structure](#repository-structure)
- [The Wiki](#the-wiki)
- [Module Descriptions](#module-descriptions)
- [Hardware](#hardware)
  - [Printed Components and Module Fit](#printed-components-and-module-fit)
- [Future development](#future-development)
- [FAQ](#faq)
- [License](#license)

## Repository Structure
- `/hardware/` – STL and STEP files for 3D printing
- `/software/` – Code for the centralized controller (in progress), example firmware for modules, and hardware test scripts
- `/docs/` – Printing instructions, and additional reference material as it becomes available (PDF)
- `/images/` – Holds images used in this README, as well as some others throughout the repository
- `README.md` – You are here.

## The Wiki
Documentation for this project, including: 

- Part orientation and printer setting recommendations
- Assembly instructions
- Calibration and hardware validation protocols
- System-level descriptions
- and more

are being migrated to the [project wiki](https://www.github.com/tyler-bartunek/KICK-Robot/wiki) for ease of access
and navigation purposes. There's a lot that goes into this system, and it is only fitting that worthy documentation
would be quite extensive, requiring a wiki to track it all. 

## Module Descriptions
Here are a few of the modules under development at present for the KICK Robot. Once these modules are fully fleshed
out, a homebrew guide will be produced and added to the wiki.

1. Wheels: This module consists of DC motors and mecanum wheels, represents minimal functional example (systems integration in process).
2. Shoeshine: Offers quadrupedal motion through use of servomotors (Pending Initial Design)
3. HexaBox: Requires six mounts, offers six-legged locomotion through use of servomotors. (Pending Initial Design)

Note that each module type gets its own uint8_t identifier. Here are some urrently used ID's within KICK framework:

| ID | Module Type |
|----|-------------|
|0x00 | **Reserved**: No Connection |
|0x01 | Echo test functionality |
|0x02 | Mecanum Wheel Version A |
|0x03 | Mecanum Wheel Version B |
|0x04 | Quadruped Leg Version A |
|0x05 | Quadruped Leg Version B |

## Hardware

### Printed Components and Module Fit
Both STEP and STL files for all components to be printed are provided under the hardware directory, with directions for
the base hardware and wheels module provided in the wiki. As modules are added, printing directions specific
to those modules will be added. This system was prototyped using an Ender 3 V2 and Cura slicer using 
PLA+, with dimensions set to reflect typical tolerances for that printer with the intent of clearance fits with minimal play between 
mounting rails and modules.

## Software
Files for characterizing your specific motors and verifying basic hardware connections to the Pi, such as the ADC for 
battery level monitoring and custom SPI fanout board PCB, are provided within this repository, as well as the base
code for the picos/modules. Module code was developed using the Raspberry Pi Pico C++ SDK and uses CMake (C++17).

ROS code for the Raspberry Pi was developed using the ros:jazzy-core docker image, and is available on a [separate repository](https://github.com/tyler-bartunek/kick_pi) for direct download on your raspberry pi once finished. Raspberry 3b+ or better strongly encouraged, as the project was developed on a 3b+. 

### Philosophy, Parent Classes: Validation Ongoing, wiki articles available upon completion
While this is explained in greater detail in the [wiki](https://www.github.com/tyler-bartunek/KICK-Robot/wiki), provided here is a brief overview
for integration purposes. Overall, the goal is for users to be able to extend this framework to arbitrary module configurations. 

#### Configuration Class (ROS)
Within this project's underlay (not to be confused with the ROS underlay), there is a kickbrain package. This package has a nested package within it
called "configuration_files". The Configuration class is defined within this subpackage, and all kinematic calculations are predicated on the geometry_msgs.msg.Twist message type coming from the motion planner, with these velocities defined relative to the center of mass, presumed or actual. 

**All user-defined configurations must inherit from the Configuration parent class and have both a fetch_commands and compute_received method defined as following signatures:** 
```
def fetch_commands(self, vel_cmd: Twist, feedback) -> list:
```

This method takes the center of mass velocity command from the motion planning node, which uses the built-in geometry\_msgs.Twist topic message type and any feedback to compute new actuator commands. 

``` 
def compute_received(self, device_data) -> Twist:
```
This method takes the data received from the bus\_hub node and computes the forward kinematics for your configuration to build feedback. 

Once you have your configuration kinematics defined, you go to the \_\_init\_\_.py file within the configuration\_files directory and add the frozenset of module ids that can be used to recognize your configuration. Note that it does use a frozenset, so if you need X number of modules for a successful deployment, be sure to add that check to your custom configuration's class definition.

__**Note that 0x00 is reserved as the "no connection" module ID, so your frozenset will need to include it if any connection points on the harness are disconnected**__

_There is a possibility that you will need to modify it directly within the kickbot_node package and rebuild it using colcon build --packages-select to achieve desired behavior, but efforts will be made to allow you to develop your own configuration definitions in an overlay._

#### Module Class (Pico)
The microcontroller code for the picos is organized in the following folder structure:

1. kick_pico: **project root, make/build from here** <br>
   a. modules: Contains the Module parent class and any subclass definition cpp and h files <br>
   b. utils: Additional cpp and header files for achieving any functionality the modules require, such as SPI communication or quadrature encoder reading <br>
   c. main.cpp: driver script, creates the `pico_device` instance and calls its `run()` method repeatedly <br>

You define your custom module by adding a header and cpp file within the modules subdirectory, and be sure to add the relevant files to the CMakeLists.txt file within that subdirectory. The custom module class that you define **must** inherit from the Module base class, and must include a run method override that defines your module's behavior in response to received data from the Pi. That run method **must** call `this -> Transfer(data)`, where `data` is a short (uint16\_t) being sent back to the pi. 

Minimally viable example of a custom subclass header file:
```
#pragma once

#include "Module.h"

class MinimalExample : public Module {
    
    public:
        
        MinimalExample();

        void run() override;

        ~MinimalExample() = default;
};
```

If your module requires additional custom header files to function, these go under the utils subdirectory and you will in turn need to modify that CMakeLists.txt file.

For example, if you need to add something for the module to read an encoder that you've either written or cloned a library for named MyReallyCoolEncLib, you would modify the very first line of CMakeLists.txt file in utils to read:

```
add_library(utils STATIC SPITools.cpp MyReallyCoolEncLib.cpp)
```

assuming that your library has a cpp file defined for it.

Lastly, you modify line 18 of main.cpp to have the name of your new module type

```
#define MODULE_TYPE MinimalExample
```

**When you define your own module definitions they must inherit from the Module base class, have a unique uint8_t ID defined, and contain a run() method override.** A sync_callback() method override is optional, but recommended if the modules need to act in a coordinated fashion (as most do). Wiki article coming soon.  

## Future development
This project is still under development, and additional details such as synchronization and timing
requirements will be made available as they are validated. Current work is focused on validating the ROS setup and getting the Wheels Module ready to ``roll". 

## FAQ

1. Why shoeboxes?

>I had originally set out to make what essentially amounts to just the wheels module as a CAD and mechatronic portfolio piece.
Seeking to understand the design considerations, I started to immerse myself in literature surrounding mecanum wheel devices 
and discovered something that is in hindsight self-evident: different design decisions like the wheel spacing and orientation 
fundamentally alters the dynamics of the system and therefore influence control. Creating modular systems to explore the impact 
of these parameters was largely underexplored in what I found, so I set out to make my own. But I needed a good frame. Something
cheap and easy to deploy. As I looked around me, I saw an unused shoebox. And the KICK Robot was born. 

>Realistically any cardboard box will work, but at the time a shoebox seemed like the right size for what I set out to accomplish.

2. Why didn't you use \<insert fastener here\> to fasten the modules to the box?

>In the early days, I explored a number of different means for mounting the hardware to the box. The current design for mounting
hardware to the box solves two problems simultaneously: the first is that of establishing a secure connection with minimal
assembly complexity, the second is offering a path for routing the wires from inside the box to the modules on the outside.

3. Doesn't the act of cutting into the box limit the reusability of a single box to test multiple design parameters?

>Yes, as do other adhesives that have enough strength to reliably anchor the hardware to the outside of the box. 

## License
As of 19 November, 2025, this project is licensed under the terms of the [Apache License-2.0](LICENSE). Software provided prior 
to this date was licensed under the terms of the MIT license, and includes the content of the directory 
`/software/Hardware Characterization/Wheels Module`. The transition to the Apache License-2.0 is to reflect that this repository
contains more than just software. 

This project also uses PyMC in the motor characterization code for the Wheels module. PyMC is also licensed under the terms
of the [Apache License-2.0](LICENSE), and also includes software licensed under the MIT license. A notice is provided in the
main directory of this repository, to underline this point and include the necessary copy of the MIT license for portions 
covered by that license.
