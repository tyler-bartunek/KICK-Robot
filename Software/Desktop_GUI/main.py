'''
This is the main file for the project. It contains the main function that runs the program.

Desktop GUI for the KICK Robot, which is a robot designed for educational purposes. 
The GUI allows users to control the robot and view its status.
This project is built using Python and PyQt6 for the GUI, and it communicates with the robot using
zeroconf for network communication and roslibpy for ROS integration.

Author: Tyler Bartunek
Date: 2024-06-01
'''

import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow



def main():
    
    #Create the application and main window, then start the event loop
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    
    main()
