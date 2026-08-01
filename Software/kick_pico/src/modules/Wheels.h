/*
 * Wheels.h
 *
 *  Created on: May 28, 2026
 *  
 *      Author: Tyler Bartunek
 */

#pragma once

#include "Module.h"
#include "drv8871_motor.h"

class Wheels : public Module{

    public:

        //Default constructor
        Wheels();

        //Override the run function to implement the desired behavior for this module
        void run() override;

        //Default destructor
        ~Wheels() = default;

    private:

        //Private member variable for the motor
        DRV8871Motor motor;

        //Private member variable for the desired speed value, which will be updated when we receive a new command from the host
        volatile short desired_command;

        //Static pointer to the current instance of the Wheels class, for use in the static callback function for the SYNC pin interrupt
        static Wheels* instance;

        //Override the sync callback to implement the desired behavior for this module when a SYNC signal is received
        void sync_callback() override;

};