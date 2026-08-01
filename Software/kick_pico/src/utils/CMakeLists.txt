#Add Quadrature decoder
add_library(QuadratureDecoder STATIC
    QuadratureDecoder.cpp
)
target_include_directories(QuadratureDecoder PUBLIC ${CMAKE_CURRENT_LIST_DIR})
pico_generate_pio_header(QuadratureDecoder
    ${CMAKE_CURRENT_LIST_DIR}/QuadratureDecoder.pio
)
target_link_libraries(QuadratureDecoder PUBLIC
    pico_stdlib
    hardware_pio
    hardware_dma
)


#Add the utils library
add_library(utils STATIC SPITools.cpp drv8871_motor.cpp)
target_include_directories(utils PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(utils PUBLIC hardware_spi hardware_pwm hardware_gpio pico_stdlib QuadratureDecoder)


