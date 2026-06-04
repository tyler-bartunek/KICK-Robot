/*
spi_test.cpp

Author: Tyler Bartunek

Test that we can receive and then send values over the SPI bus on the raspberry pi pico
*/

//#define and #include
#include "Module.h"
#include<iostream> // For debugging purposes, can be removed later


/****************************Main Function  *******************************/

//Static wrapper function definitions
static bool blink_callback(struct repeating_timer *t) {
    // Cast the user data back to a Module pointer
    Module* module = static_cast<Module*>(t->user_data);
    // Call the member function to handle blinking
    module->ErrorMessage(); // Run the error message handler, which will determine the appropriate blinking pattern based on the current error code
    return true; // Return true to keep the timer repeating
}




Module::Module(const uint8_t identifier){

    //Start up SPI
    int rc = this->spi.init();
    hard_assert(rc == PICO_OK);

    //Set the mask for checksums: based on module ID
    MASK = identifier;

    //Initialize the LED to blink
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);

    //Set up the repeating timer for blinking error codes, with the static wrapper function as the callback and passing 'this' as user data
    //fire every 50 ms, which is the smallest delay we will use between blinks, so that we can maintain accurate timing even when we have to do a lot of blinks.
    add_repeating_timer_ms(50, blink_callback, this, &blink_timer);

    //Initialize SYNC pin
    gpio_init(SYNC);
    gpio_set_dir(SYNC, GPIO_IN);

    //Start blinking timers
    error_code = LOST_HOST;
    burst_time = to_ms_since_boot(get_absolute_time());
    blink_time = to_ms_since_boot(get_absolute_time());
    blinks_done = 0;
    in_burst = true;
    led_on = false;

}

//Handle SPI transaction
int Module::Transfer(int data){

    switch(status){

        case DISCOVERY:

            {
            //Create sync and handshake attempt arrays
            uint8_t sync_message[MSG_LEN] = {};
            uint8_t handshake_attempt[MSG_LEN] = {};

            //Enforce transmission rules, sync message has 0-valued data
            this->FrameMessage(0, sync_message);

            //Send out the sync message
            this->spi.transfer(sync_message, handshake_attempt, MSG_LEN);

            if (this->IsConnectionEstablished(handshake_attempt)){
                PATH_ID = handshake_attempt[1] & 0x7;
                status = TRANSMITTING;
                return 0; //Known value sent by host on successful handshake, can be used to trigger state changes in the module's run() method if desired
            }
            else{
                //Send to DISCONNECTED so we have a path to re-try.
                status = DISCONNECTED;
                prev_status = DISCOVERY;
            }

            }

            break;

        case TRANSMITTING:
            {

            //Get the outgoing message ready to send
            uint8_t sending[MSG_LEN] = {};
            this->FrameMessage(data, sending);
            //Prep the vector for receiving: force it to be the right size
            uint8_t receiving[MSG_LEN];

            //Perform the SPI transfer
            this->spi.transfer(sending, receiving, MSG_LEN);
            //Parse the message
            int received = this->ParseMessage(receiving);

            return received;
            }

            break;

        case SUSPECT:

            if ((prev_status == SUSPECT) && (missed_packets >= 3)){
                status = DISCONNECTED;
                error_code = LOST_HOST;
            }
            else{
                missed_packets++;
                status = TRANSMITTING; //Try again, without discovery protocol to see if we can get lucky
            }

            break;

        case DISCONNECTED:
        default:

            status = DISCOVERY;

            break;
    }

    return 0;

}


//Frame the outgoing message
void Module::FrameMessage(int data, uint8_t* message){

    //Construct the header, push the mask to host
    message[0] = 0xF0 | (PATH_ID & 0x7);
    message[1] = MASK;

    if ((this-> status == TRANSMITTING) || (this->status == DISCOVERY)){

        // Use bitwise operations to break the 'int' into 4 bytes
        // Higher byte: Shift right by 8 bits and mask lowest 8 bits (optional mask but clear)
        for (uint8_t byte_idx = 0; byte_idx < WORD_LEN; byte_idx++){
            message[2 + byte_idx] = (data >> (8 * (WORD_LEN - 1 - byte_idx))) & 0xFF;
        }

        //Compute the checksum value based on first message length-2 values
        //this value because message length - (alignment + checksum)
        message[6] = this->Checksum(message, MSG_LEN - 2);

    }
    else{
        //Push out a message of zeros with 0xFF checksum
        message[6] = 0xFF;
    }

    //Append alignment byte regardless.
    message[7] = 0xBF;
 
}


//Parse the incoming message
int Module::ParseMessage(const uint8_t* message){

    bool correct_path_id = (message[1] & 0x7) == PATH_ID;
    bool correct_mask = message[2] == MASK;
    uint8_t data_payload[MSG_LEN-2]= {message[1], message[2], message[3], message[4], message[5], message[6]}; //Strip the header and alignment bytes for checksum validation
    bool correct_checksum_value = this->ValidChecksum(data_payload, message[7], MSG_LEN - 2);

    if (correct_path_id && correct_checksum_value && correct_mask){
        status = TRANSMITTING;
        error_code = ALL_CLEAR;
        prev_status = TRANSMITTING;
        missed_packets = 0;
        int value = 0;
        //Reconstruct the int from the 4 bytes in the message, using bitwise operations using a for loop
        for (uint8_t byte_idx = 0; byte_idx < WORD_LEN; byte_idx++){
            value |= (message[3 + byte_idx] << (8 * (WORD_LEN - 1 - byte_idx)));
        }
        return value;
    }
    else{
        status = SUSPECT;
        prev_status = SUSPECT;
        if (!correct_path_id){
            error_code = BAD_PATH_ID;
        }
        else if (!correct_checksum_value){
            error_code = BAD_CHECKSUM;
        }
        else if (!correct_mask){
            error_code = BAD_MASK;
        }
        return 0;
    }

}

void Module::ErrorMessage(){

    switch(error_code){
        case ALL_CLEAR:
            //Bypass the Blink method, just keep it on.
            gpio_put(PICO_DEFAULT_LED_PIN, true);
            break;

        case BAD_PATH_ID: //Have this cascade for now.

        case BAD_MASK:
            this->Blink(2, 250);
            break;

        case BAD_CHECKSUM:
            this->Blink(4, 250);
            break;

        case LOST_HOST:
        default:
            this -> Blink(2, 1000);
            break;
    }

}

void Module::Blink(const uint8_t num_blinks, const uint64_t delay_between_blinks){

    uint64_t now = to_ms_since_boot(get_absolute_time());

    /* Start a new burst once per second */
    if (!in_burst && ((now - burst_time) >= 1000)) {
        in_burst = true;
        blinks_done = 0;
        led_on = false;

        gpio_put(PICO_DEFAULT_LED_PIN, led_on);

        blink_time = now;
        burst_time = now;
        return;
    }

    /* If we're not in a burst, do nothing */
    if (!in_burst) {
        return;
    }

    /* Handle blinking inside the burst */
    if ((now - blink_time) >= delay_between_blinks) {
        led_on = !led_on;
        gpio_put(PICO_DEFAULT_LED_PIN, led_on);

        blink_time = now;

        /* Count only ON transitions as a blink */
        if (led_on) {
            blinks_done++;
            if (blinks_done >= num_blinks) {
                in_burst = false;
                led_on = false;
                gpio_put(PICO_DEFAULT_LED_PIN, led_on);
            }
        }
    }
}

bool Module::IsConnectionEstablished(const uint8_t* handshake){

    bool eof_check = handshake[0] == 0xBF;
    //Strip the alignment and checksum bytes from checksum calc
    uint8_t data_payload[MSG_LEN-2];
    for (uint8_t byte_idx = 1; byte_idx < MSG_LEN - 1; byte_idx++){
        data_payload[byte_idx - 1] = handshake[byte_idx];
    }
    bool checksum_valid = this -> ValidChecksum(data_payload, handshake[MSG_LEN - 1], MSG_LEN-2);

    return eof_check && checksum_valid;

}


uint8_t Module::Checksum(const uint8_t* payload, size_t payload_len){

    uint8_t result = 0;

    for (uint8_t byte_idx = 0; byte_idx < payload_len; byte_idx++){
        result += payload[byte_idx];
    }

    return result;

}

bool Module::ValidChecksum(const uint8_t* payload, uint8_t sent_result, size_t payload_len){

    return this->Checksum(payload, payload_len) == sent_result;

}