from gi.repository import Gtk
import mapnik

class PreviewWindow(Gtk.Window):
    def __init__(self, preview_image, main_window):
        self.previewImage = preview_image
        self.main_window = main_window
        
        #this window is not loaded from a pre-defined *.glade file
        #it is generated on-the-fly
        Gtk.Window.__init__(self, title="Preview for extent")
        self.box = Gtk.VBox(spacing=2)
        self.add(self.box)
                        
        self.image = Gtk.Image()
        self.initImage()
        self.box.pack_start(self.image, True, True, 0)
        
        #This is very necessary for an additional window...it handles the click on the close button of the window
        self.connect("delete-event", self.closedThisWindow)
        self.closed = True
        
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
    def getStatus(self):
        return self.closed
        
    def initImage(self):
        self.image.set_from_file("./data/media/back.png")        
        
    def on_button_reload_clicked(self, widget):
        self.reloadImage()
        
    def getWindow(self):
        return self
        
    def reloadImage(self):
        self.image.set_from_file(self.previewImage)
        
    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_preview.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_preview.get_label())
            self.show_all()
            self.closed = False
        
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_preview.set_label(self.main_window.ui.mnu_preview.get_label().split(self.main_window.menuItemIndicator)[1])
            self.hide()
            self.closed = True
    
    def destroyWindow(self):
        self.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_preview.set_label(self.main_window.ui.mnu_preview.get_label().split(self.main_window.menuItemIndicator)[1])


    
