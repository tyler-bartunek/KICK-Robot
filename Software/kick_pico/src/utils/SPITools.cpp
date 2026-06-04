/*
SPITools.cpp

Author: Tyler Bartunek

Flesh out the methods that belong to the SPI_Bus object
*/

//#define and #include
#include "SPITools.h"
#include <iostream> // For debugging purposes, can be removed later


//Constructor: 
SPI_Bus::SPI_Bus(const uint8_t cs, const uint8_t copi, const uint8_t cipo, const uint8_t sck){
    CS = cs;
    COPI = copi;
    CIPO = cipo;
    SCK = sck;
}

//Default Constructor: Uses pinout defined in header file
SPI_Bus::SPI_Bus(){}

int SPI_Bus::init(){

        spi_init(spi0, 100);                                            // value of 100 is baud rate, ignored in peripheral mode
        spi_set_format(spi0, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST); // Only sending one byte in this test anyway
        spi_set_slave(spi0, true);                                      // Set the device to be in peripheral mode

        // Configure CS, COPI, CIPO, and SCK pins
        gpio_set_function(CS, GPIO_FUNC_SPI);
        gpio_disable_pulls(CS);
        gpio_set_function(CIPO, GPIO_FUNC_SPI);
        gpio_set_function(COPI, GPIO_FUNC_SPI);
        gpio_set_function(SCK, GPIO_FUNC_SPI);

        // Make the SPI pins available to picotool
        bi_decl(bi_4pins_with_func(CIPO, COPI, SCK, CS, (uint32_t)GPIO_FUNC_SPI)); //RX, TX, SCK, CS

        return PICO_OK; // Defined in stdlib as 0 (pico-sdk/src/common/pico_base_headers/include/pico/error.h on github)
}


void SPI_Bus::transfer(const uint8_t* data, uint8_t* rx, size_t BUF_LEN){
    //Receives and returns data to the controller over the SPI bus

    //std::cout statements are artifact of debugging.
    // std::cout << "Waiting for valid transfer" << std::endl;

    // if (spi_is_readable(spi0)){
        uint8_t sync = 0;
        while(sync != 0xBF){
            //Send 0xBF until we get a response of 0xBF, which indicates that the controller is ready to send data.
            spi_write_read_blocking(spi0, &data[0], &sync, 1);
        }
        rx[0] = 0xBF;

        for(size_t i = 1; i < BUF_LEN; i++){
            spi_write_read_blocking(spi0, &data[i], &rx[i], 1);
        }
    // }
    // else{
    //     //If it failed, return a 0-valued array.
    //     // std::cout << "Unable to find anything, trying again" << std::endl;
    //     for (uint8_t i = 0; i < BUF_LEN; i++){
    //         rx[i] = 0;
    //     }
    // }

    // Debugging: Add back in if unsure what we're receiving
    // for (size_t i = 0; i < BUF_LEN; i++){
    //     std::cout << "\tByte " << int(i) << ": " << std::hex << int(rx[i]) << std::endl;
    // }

}
