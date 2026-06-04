/* drv8871_motor.cpp 
    *
    *  Created on: Apr 1, 2023
    *  
*/

#include "drv8871_motor.h"

#define GEAR_RATIO 19
#define ENCODER_COUNTS_PER_REVOLUTION 44

//Utiltiy function for setting pwm_set_enabled and and set_function for a given pair of pins
void set_drive_pins(uint8_t dir, uint8_t pwr) {

    pwm_set_enabled(pwm_gpio_to_slice_num(dir), false);
    pwm_set_enabled(pwm_gpio_to_slice_num(pwr), true);

    gpio_set_function(dir, GPIO_FUNC_SIO);
    gpio_set_function(pwr, GPIO_FUNC_PWM);

}

DRV8871Motor::DRV8871Motor() {
    //Default constructor implementation: Use default GPIO pin values set in the header file.

    //These would be in1_pin = 27;
    //in2_pin = 28;
    //encoder_a_pin = 12;
    //encoder_b_pin = 13;

    //Again, in1_pin and in2_pin need to be on separate slices, so the default pinout is set up that way.
    //Also, encoder_a_pin and encoder_b_pin need to be on adjacent pins for the encoder library to work, so the default pinout is set up that way as well.
}

DRV8871Motor::DRV8871Motor(uint8_t in1_pin, uint8_t in2_pin, uint8_t encoder_a_pin, uint8_t encoder_b_pin) {
    //Constructor implementation with parameters for the GPIO pins
    this->in1_pin = in1_pin;
    this->in2_pin = in2_pin;

    //Assert that in1 and in2 pins are not on the same slice, since they need to be on separate slices for independent control of direction and speed
    hard_assert(pwm_gpio_to_slice_num(in1_pin) != pwm_gpio_to_slice_num(in2_pin));

    //Set the encoder pins for the encoder library
    this->encoder_a_pin = encoder_a_pin;
    this->encoder_b_pin = encoder_b_pin;
}

void DRV8871Motor::init() {
    //Initialize the GPIO pins for the motor driver

    //Initialize the IN1 and IN2 pins as outputs
    gpio_init(in1_pin);
    gpio_init(in2_pin);
    gpio_set_dir(in1_pin, GPIO_OUT);
    gpio_set_dir(in2_pin, GPIO_OUT);

    //Initialize the encoder pins as inputs
    gpio_init(encoder_a_pin);
    gpio_init(encoder_b_pin);
    gpio_set_dir(encoder_a_pin, GPIO_IN);
    gpio_set_dir(encoder_b_pin, GPIO_IN);

    //Call the begin function of the encoder library to initialize the encoder
    this->encoder.init(pio0); //Initialize the encoder with the specified PIO instance. This will set up the necessary PIO state machines and interrupts for reading the encoder signals.
    encoder_idx = this->encoder.addQuadratureEncoder(encoder_a_pin); //Technically, we only need to add one of the encoder pins to the encoder library since it will read both signals from the quadrature encoder, but we will use the encoder_a_pin as the base pin for the library's purposes.
    
    //Set the PWM frequency to the default, override by calling this method before you call drive().
    this->set_pwm_frequency(in1_pin, in2_pin, 125, 1000); //Set the PWM frequency to 1 kHz with a divider of 125 for a base clock of 125 MHz. This is a common frequency for motor control, but can be adjusted as needed for different motors or applications.

    this->last_encoder_time = get_absolute_time(); //Initialize the last encoder time to the current time
}

void DRV8871Motor::drive(short speed_value) {
    //Set the motor speed and direction based on the input speed value
    //Speed is a short and has values from the minimum of -32768 to the maximum of 32767. The sign of the speed value determines the direction of the motor, with positive values indicating forward direction and negative values indicating reverse direction. The magnitude of the speed value determines the speed of the motor, with larger absolute values corresponding to higher speeds. The actual mapping of speed values to PWM duty cycle will depend on the specific implementation and requirements of the motor control system.


    //Set the direction and speed pins accordingly
    if (speed_value > 0) {
        direction = true; //Forward

        direction_pin = in1_pin;
        speed_pin = in2_pin;

    } else if (speed_value < 0) {
        direction = false; //Reverse

        direction_pin = in2_pin;
        speed_pin = in1_pin;

    } else{
        this->brake_motor(); //If speed is zero, brake the motor
        return;
    }

    if ((direction != prev_direction) || (braked && speed_value != 0)) { //If we are changing direction or if we were previously braked and are now trying to set a nonzero speed, we need to update the drive pins accordingly
        
        prev_direction = direction; //Update the previous direction variable
        braked = false; //If we were previously braked, we are no longer braked since we are now changing direction and setting a nonzero speed
        set_drive_pins(direction_pin, speed_pin); //Set the drive pins for the new direction. This will disable the PWM on the previous speed pin and set the new direction pin to GPIO function for controlling the motor direction, while setting the new speed pin to PWM function for controlling the motor speed.

    }

    gpio_put(direction_pin, 1); //Set the direction pin high to maintain the current direction
    uint16_t pwm_value = (uint16_t)((abs(speed_value) / 10000.0f) * wrap); //Calculate the PWM value based on the absolute value of the speed. This maps the speed range of -10000 to 10000, where a speed of zero will correspond to a PWM of wrap, and a speed of \pm 10000 will correspond to a PWM of zero. The factor of 10000 is used to scale the speed value to the range of the PWM wrap value, which allows for finer control of the motor speed.
    pwm_set_gpio_level(speed_pin, wrap - pwm_value); //Set the speed pin to the wrap complement of the calculated PWM value, as full duty cycle corresponds to brake condition.

    //Do regardless: get/update counts and speed
    this->get_encoder_counts();
    this->get_speed();

}

void DRV8871Motor::brake_motor() {
    //Disable PWM on both pins
    pwm_set_enabled(pwm_gpio_to_slice_num(in1_pin), false);
    pwm_set_enabled(pwm_gpio_to_slice_num(in2_pin), false);

    //Set the motor to brake mode, which should stop the motor more quickly than just setting speed to zero. This is done by setting both IN1 and IN2 pins to the same value (either both high or both low) according to the DRV8871 datasheet.
    gpio_set_function(in1_pin, GPIO_FUNC_SIO); //Set IN1 pin to GPIO function for braking
    gpio_set_function(in2_pin, GPIO_FUNC_SIO); //Set IN2 pin to GPIO function for braking

    gpio_put(in1_pin, 1);
    gpio_put(in2_pin, 1);

    braked = true; //Update the braked variable to indicate that the motor is currently braked
}

void DRV8871Motor::set_pwm_frequency(uint8_t pin_1, uint8_t pin_2, uint8_t divider, uint32_t frequency) {

    //Get the slice number for the IN2 pin, which is used for PWM speed control
    uint8_t pwm_slice_1 = pwm_gpio_to_slice_num(pin_1);
    uint8_t pwm_slice_2 = pwm_gpio_to_slice_num(pin_2);

    //Set the PWM frequency by configuring the clock divider for the PWM slice
    pwm_set_clkdiv(pwm_slice_1, divider); //Set the clock divider for the PWM slice to adjust the frequency. The actual frequency will depend on the base clock frequency of the PWM and the divider value. For example, if the base clock is 125 MHz and the divider is set to 125, the resulting PWM frequency would be 1 MHz.
    pwm_set_clkdiv(pwm_slice_2, divider); //Set the clock divider for the PWM slice to adjust the frequency. The actual frequency will depend on the base clock frequency of the PWM and the divider value. For example, if the base clock is 125 MHz and the divider is set to 125, the resulting PWM frequency would be 1 MHz.

    //Calculate the wrap value for 16-bit resolution based on the desired PWM frequency. This allows for a range of speed values from -32768 to 32767, where the wrap value determines the maximum count value for the PWM counter before it resets to zero.
    wrap = ((125000000 / divider) / frequency) - 1; //Calculate the wrap value based on the base clock frequency, divider, and desired PWM frequency. For example, if the base clock is 125 MHz, the divider is 125, and the desired frequency is 1 kHz, the resulting wrap value would be 1000, which means the PWM counter will count from 0 to 999 before resetting to zero.
    pwm_set_wrap(pwm_slice_1, wrap); //Set the wrap value for the PWM slice to adjust the resolution and range of speed values.
    pwm_set_wrap(pwm_slice_2, wrap); //Set the wrap value for the PWM slice to adjust the resolution and range of speed values.
}

void DRV8871Motor::set_encoder_filter_parameter(float new_alpha){
    this->alpha = new_alpha;
}

void DRV8871Motor::get_encoder_counts() {
    //Utility function to get the current encoder counts for debugging purposes
    this->counts = this->encoder.getCount(this->encoder_idx); //Get the current encoder counts using the encoder library's getCount function, which reads the current count value from the specified encoder index. This allows for tracking the position and speed of the motor based on the encoder readings.
}


void DRV8871Motor::get_speed() {
    
    //Compute the time since the last encoder reading
    absolute_time_t current_time = get_absolute_time();
    float dt = absolute_time_diff_us(last_encoder_time, current_time) / 1000000.0; //Convert time difference to seconds

    int32_t encoder_diff = counts - prev_encoder_counts; //Calculate the change in encoder counts

    //Overflow/underflow protection: variables for checking the sign of counts vs prev_encoder_counts
    //Since it's 32-bit integers, we want to shift everything by 31 bits to extract the sign.
    bool count_sign_check = (bool)(counts >> 31);
    bool prev_sign_check = (bool)(prev_encoder_counts >> 31);

    //Calculate the new speed based on the change in encoder counts, gear ratio, and counts per revolution to obtain speed in millirad/s 
    //Gear ratio is GEAR_RATIO:1 reduction, PicoEncoder counts per revolution is ENCODER_COUNTS_PER_REVOLUTION
    new_speed = (int)(((float)encoder_diff * 2.0f * M_PI * 1000.0f) / (dt * GEAR_RATIO * ENCODER_COUNTS_PER_REVOLUTION)); //Calculate the new speed in millirad/s based on the change in encoder counts, time interval, gear ratio, and counts per revolution. The factor of 1000 is used to convert from rad/s to millirad/s for better resolution in the speed value.

    //Check if the sign of counts changed without a change in direction. 
    if ((direction == prev_direction) && (count_sign_check ^ prev_sign_check)){
        //If it did, as a sanity measure stopgap, assume the speed didn't actually change (good assumption for small dt).
        this->speed = prev_speed;
    }
    else{
        //Apply a weighted average filter to the new speed value to smooth out noise in the encoder readings. 
        //The alpha parameter determines the weight given to the new speed value versus the previous speed value, 
        //with a smaller alpha giving more weight to the previous speed and a larger alpha giving more weight to the new speed.
        this->speed = (int)((this->alpha * new_speed) + ((1 - this->alpha) * prev_speed)); //Apply the weighted average filter to the new speed value
    }

    prev_encoder_counts = counts; //Update previous encoder counts for the next iteration
    last_encoder_time = current_time; //Update the last encoder time to the current time
    prev_speed = this->speed; //Update the previous speed value for the next iteration

}
