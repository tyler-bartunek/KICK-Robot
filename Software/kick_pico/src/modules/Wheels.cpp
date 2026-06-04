
#include "Wheels.h"


Wheels* Wheels::instance = nullptr; // Initialize the static instance pointer to nullptr


Wheels::Wheels() : Module(0x02) { // Set the module ID to 0x02 for the wheels module

    //Initialize the motor
    motor.init();

    //Set the filter parameter for the encoder readings to something reasonable, to smooth out the speed readings without introducing too much lag. 
    //This is a bit of a magic number that I found through testing, but it seems to work well for my setup.
    motor.set_encoder_filter_parameter(0.001);


    instance = this; // Set the static instance pointer to the current instance of the Wheels class, so that we can use it in the static callback function for the SYNC pin interrupt
    //Set sync_callback to trigger on the SYNC pin on falling edge, so that the speed command across modules updates at the same cadence.
    gpio_set_irq_enabled_with_callback(SYNC, GPIO_IRQ_EDGE_FALL, true, [](uint gpio, uint32_t events) -> void {
        if (events & GPIO_IRQ_EDGE_FALL) {
            // Call the sync_callback method of the Wheels instance
            Wheels::instance->sync_callback();
        }
    });

}

void Wheels::run() {

    //Get the incoming message, which should be a speed value for the motor
    this->desired_command = this->Transfer(this->motor.speed); // The argument here is the velocity feedback from the motor, which the host can use for closed-loop control if desired. The return value is the new desired speed command from the host, which we will use to update the motor speed in the sync_callback when we receive a SYNC signal.

}

void Wheels::sync_callback() {

    //For this module, only drive the motor with the newly received command when we receive a SYNC signal, which indicates that the host has sent 
    // a new command and we should update our behavior accordingly. This is to ensure that we don't have any issues with missed packets or 
    // desynchronization between the host and the module.
    this->motor.drive(desired_command);

    //Reset the error code and blinking state in case we were in an error state before
    error_code = ALL_CLEAR;

}