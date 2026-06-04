/*
 * drv8871_motor.h: Header file for the DRV8871Motor class, which provides an interface for controlling a 
 * motor using the DRV8871 motor driver and reading encoder counts and speed from a quadrature encoder. 
 * 
 * This class is designed to be used with the Raspberry Pi Pico and the RP2040 microcontroller, 
 * utilizing the hardware PWM and GPIO capabilities of the chip for motor control, as well as a 
 * PIO-based quadrature encoder library for reading encoder signals (credit given below). The class 
 * provides methods for initializing the motor driver, setting motor speed and direction, braking 
 * the motor, changing PWM frequency, and getting encoder counts and speed readings. The motor 
 * speed is controlled by setting the duty cycle of the PWM signal on one of the IN pins of the 
 * DRV8871, while the direction is controlled by which IN pin is set to high. The class also 
 * includes functionality for braking the motor by setting both IN pins to the same value, which 
 * should stop the motor more quickly han just setting speed to zero.
 * 
 * Credit due to adamgreen for their excellent PIO-based quadrature encoder library, which is 
 * used in this class for reading encoder signals in the background using interrupts. The library 
 * can be found at https://github.com/adamgreen/QuadratureDecoder. 
 * 
 * I sincerely apologize for having to rip their header, cpp, and pio files out of that repository and 
 * copying them directly into this project, but CMake and FetchContent were giving me a lot of 
 * trouble when trying to include the library as a submodule or external project. This was simpler.
 *
 *  Created on: May 10, 2026
 *  Last edited on: May 16, 2026
 *      Author: tyler-bartunek
 */

#pragma once

#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"

#include <cmath>

//Include the header file for the rotary encoder library
#include "QuadratureDecoder.h"

class DRV8871Motor {

    public: 

        //Default constructor prototype
        DRV8871Motor();

        //Constructor prototype with parameters for the GPIO pins
        DRV8871Motor(uint8_t in1_pin, uint8_t in2_pin, uint8_t encoder_a_pin, uint8_t encoder_b_pin);

        //Function prototype for initializing the motor driver
        void init();

        //Function prototype for setting the motor speed and direction
        //speed_value should be an integer value between -10000 and 10000, 
        //corresponding to 100% reverse and 100% forward, respectively (with 
        //two bonus decimal places available on those percentage points)
        void drive(short speed_value);

        //Function prototype for braking the motor
        void brake_motor(); 

        //Function prototype for changing PWM frequency and duty cycle (if necessary)
        //Sets both pins simultaneously. 
        void set_pwm_frequency(uint8_t pin_1, uint8_t pin_2, uint8_t divider, uint32_t frequency);

        //Function prototype for setting weighted average filter parameter for encoder readings
        void set_encoder_filter_parameter(float new_alpha);

        //Function prototype for getting the current encoder counts for debugging purposes
        void get_encoder_counts();

        //Function prototype for mapping to speed from encoder readings
        void get_speed();

        //Default destructor
        ~DRV8871Motor() = default;

    private:

        //Private member variables for the GPIO pins, set to default pinouts for the pico in my setup
        //Note that the IN1 and IN2 pins need to be on separate PWM slices for independent control of direction and speed.
        uint8_t in1_pin = 27;
        uint8_t in2_pin = 28;
        //Encoder pins need to be adjacent for the encoder library to work. Technically, b isn't actually used in this libary,
        //but we will still set it up for the sake of completeness and potential future use.
        uint8_t encoder_a_pin = 12;
        uint8_t encoder_b_pin = 13;

        //Flags for keepin track of the motor state for use in setting the drive pins
        bool prev_direction = false; //Variable to store the previous direction of the motor for use in calculating speed from encoder readings, forward true
        bool direction = true;
        bool braked = false; //Variable to store whether the motor is currently braked or not, for use in calculating speed from encoder readings
        
        //Placeholder variables for the drive pins, which are set in the drive() method based on 
        //the desired direction of the motor. With the way the DRV8871 works, you can toggle direction
        //by switching which pin is high and which pin is PWM capable for speed control. direction pin
        //is always high. Speed pin being low corresponds to full speed, so the PWM value is... inverted.
        uint8_t direction_pin;
        uint8_t speed_pin;

        //Variable for storing the PWM wrap value based on the desired frequency and divider.
        //This is set in the set_pwm_frequency() method and is used to calculate the PWM value in drive().
        uint32_t wrap; 

        //Encoder object and index for reading the encoder counts in the background.
        QuadratureDecoder encoder = QuadratureDecoder(); //Encoder object instance from the QuadratureDecoder library
        uint32_t encoder_idx;

        //For computing speed from encoder readings
        //Time since last encoder reading, for calculating speed from encoder counts
        absolute_time_t last_encoder_time; //Initialize to zero time

        volatile int32_t prev_encoder_counts = 0; //Variable to store the current encoder counts for calculating speed

        //Filter parameters
        float alpha = 1; //Default value for the weighted average filter parameter for encoder readings, means toss old readings
        volatile int new_speed = 0; //Variable to store the new speed value calculated from encoder readings after applying the filter
        float dt = 0.01; //Time interval for calculating speed from encoder readings, in seconds
        volatile int prev_speed = 0; //Variable to store the previous speed value for use in the weighted average filter
        

    public:

        //Current encoder counts and speed, stored as volatile for safe access across different contexts (main loop and interrupts)
        volatile int32_t counts = 0;
        volatile int speed = 0;
};  