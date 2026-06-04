#Add my subdirectories
add_subdirectory(utils)
add_subdirectory(modules)

#Add the main.cpp file as an executable
add_executable(kick_module main.cpp)

#Link my libraries
target_link_libraries(kick_module PRIVATE modules pico_stdlib)

pico_enable_stdio_usb(kick_module 1)
pico_enable_stdio_uart(kick_module 0)

pico_add_extra_outputs(kick_module)

