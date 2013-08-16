from gi.repository import Gtk
import mapnik
import time
import os


class ToolsWindow(Gtk.Window):
    
    def __init__(self, logfiles, main_window, name = "tools_window", file = "./data/ui/Toolbars.glade"):
        self.logfiles = logfiles
        self.main_window = main_window
                
        #basics for loading a *.glade file
        self.builder = Gtk.Builder()
        self.builder.add_from_file(file)
        self.window = self.builder.get_object(name)
        
        self.initializeContents()
        
        #This is very necessary for an additional window...it handles the click on the close button of the window
        self.window.connect("delete-event", self.closedThisWindow)
        self.closed = True
 
###Initializations 
    def initializeContents(self):
        self.button_zoom_in = self.builder.get_object('button_zoom_in')
        self.button_zoom_in.connect("clicked", self.on_button_zoom_in_clicked)
        self.button_zoom_out = self.builder.get_object('button_zoom_out')
        self.button_zoom_out.connect("clicked", self.on_button_zoom_out_clicked)
        self.button_up = self.builder.get_object('button_up')
        self.button_up.connect("clicked", self.on_button_up_clicked)
        self.button_down = self.builder.get_object('button_down')
        self.button_down.connect("clicked", self.on_button_down_clicked)
        self.button_right = self.builder.get_object('button_right')
        self.button_right.connect("clicked", self.on_button_right_clicked)
        self.button_left = self.builder.get_object('button_left')
        self.button_left.connect("clicked", self.on_button_left_clicked)
        self.button_reload = self.builder.get_object('button_reload')
        self.button_reload.connect("clicked", self.on_button_reload_clicked)
        
        
    def initializeTilesWindow(self, tiles_window):
        self.tiles_window = tiles_window
        
    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_tools.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_tools.get_label())
            self.window.show_all()
            self.closed = False
            
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_tools.set_label(self.main_window.ui.mnu_tools.get_label().split(self.main_window.menuItemIndicator)[1])
            self.window.hide()
            self.closed = True
            
    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_tools.set_label(self.main_window.ui.mnu_tools.get_label().split(self.main_window.menuItemIndicator)[1])
            
###Listeners
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
    def on_button_zoom_in_clicked(self, widget):
        self.tiles_window.scaling('in')
        
    def on_button_zoom_out_clicked(self, widget):
        self.tiles_window.scaling('out')
        
    def on_button_up_clicked(self, widget):
        self.tiles_window.navigate('up')
        
    def on_button_down_clicked(self, widget):
        self.tiles_window.navigate('down')
        
    def on_button_right_clicked(self, widget):
        self.tiles_window.navigate('right')
    
    def on_button_left_clicked(self, widget):
        self.tiles_window.navigate('left')
        
    def on_button_reload_clicked(self, widget):
        self.tiles_window.reloadMapView()
        
###Functions

    def getStatus(self):
        return self.closed