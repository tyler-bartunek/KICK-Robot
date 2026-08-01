/*
BlinkEcho.cpp

Author: Tyler Bartunek

Blinks when disconnected, echos data with the LED steady when connected.
*/

//#define and #include
#include "EchoDevice.h"

//Constructor
EchoDevice::EchoDevice() : Module(0x01){}

void EchoDevice::run(){

    //Echo received messages back
    this->Echo();
    // this->ErrorMessage();

}


void EchoDevice::Echo(){

    //Initialize data_to_send and data_received
    static int data_to_send = 0;
    int data_received = 0;

    //Check if we are transmitting or if we've lost connection. If we have then we want to know about it
    data_received = this->Transfer(data_to_send);
    if ((status != DISCOVERY) && (status != TRANSMITTING))
        data_received = -626; //Value unlikely to appear by accident in transfer, means bad

    //Ensure that data_to_send becomes what we received
    data_to_send = data_received;

}
