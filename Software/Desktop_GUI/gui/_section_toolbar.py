
from PyQt6.QtWidgets import (
    QWidget, QMenuBar, QMenu
)
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtCore import Qt, pyqtSignal


class Toolbar(QMenuBar):
    
    #TODO: Define signals to connect to slots later
    
    def __init__(self, parent = None):
        super().__init__(parent)
        
        
        #Create the dropdown menus for the toolbar
        self.add_file_dropdown()
        self.add_edit_dropdown()
        self.add_view_dropdown()
        self.add_tools_dropdown()
        
        
        
    def add_file_dropdown(self) -> None:
        
        file_menu = self.addMenu("File")
        
        save_action = QAction("Save Configuration As", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        load_action = QAction("Load Configuration", self)
        load_action.setShortcut("Ctrl+O")
        file_menu.addAction(load_action)
        
        #Action to create a new locomotion type via wizard
        new_locomotion_action = QAction("New Locomotion Type", self)
        new_locomotion_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_locomotion_action)
        
        #Separator between the new locomotion type and the exit action
        file_menu.addSeparator()
    
        #Action to exit the application
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        file_menu.addAction(exit_action)
        
    
    def add_edit_dropdown(self) -> None:
        
        edit_menu = self.addMenu("Edit")
        
        sensor_configs_action = QAction("Sensor Setting Files", self)
        
        #Add something to edit sensor config menu
        edit_menu.addAction(sensor_configs_action)
        
        #Edit the locomotion type wizard
        locomotion_type_action = QAction("Module Setting Files", self)
        edit_menu.addAction(locomotion_type_action)

    
    def add_view_dropdown(self) -> None:
        
        view_menu = self.addMenu("View")
        
        hardware_config_action = QAction("Hardware Configuration", self)
        view_menu.addAction(hardware_config_action)
        
    
    
    def add_tools_dropdown(self) -> None:
        
        tools_menu = self.addMenu("Tools")
        
        SSH_terminal_action = QAction("SSH Terminal", self)
        tools_menu.addAction(SSH_terminal_action)
        
    
    
