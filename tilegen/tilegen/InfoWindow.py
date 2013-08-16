from gi.repository import Gtk
import mapnik
import time
import os

from tilegen import rendering
from tilegen import gdal_functions as gdal
from tilegen import postgreFunctions as postgre

class InfoWindow(Gtk.Window):

    def __init__(self, logfiles, main_window, name = "InformationRetrievalWindow", file = "./data/ui/InfoWindow.glade"):
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
        self.textview1 = self.builder.get_object('textview1')
        self.textview2 = self.builder.get_object('textview2')
        self.textview3 = self.builder.get_object('textview3')
        self.textview4 = self.builder.get_object('textview4')
        self.textview5 = self.builder.get_object('textview5')
        self.textview6 = self.builder.get_object('textview6')
        self.textview7 = self.builder.get_object('textview7')
        self.textview8 = self.builder.get_object('textview8')
        self.textview9 = self.builder.get_object('textview9')
        
    def initializeTextviewsSeperately(self):
        self.setTextviews('') 
        
    def initializeInfoWindow(self, mapnik_map, tile_window, styling_window):
        self.mapnik_map = mapnik_map
        self.tile_window = tile_window
        self.styling_window = styling_window
        
        self.datasource = self.styling_window.datasource
        self.filter = self.styling_window.filter
        
        self.setTextviews('') 
           
        tileBunch, maxZoom = self.tile_window.getParameterForGeneralisation()
        text_array = []
            
        for tile in tileBunch:
            infos = []
            text = 'Tile= x:' + str(tile[0]) + ' | y:'+ str(tile[1]) +'\n'
            #infos of the tile that should be processed
            self.tileproj = rendering.GoogleProjection(maxZoom+1)
            extent, z, extent_geo = self.tile_window.getExtents(tile, self.tileproj)
            
            featCount = 0
            #print self.datasource[0]
            if self.datasource[0] == 'shape':
                featCount, inner_distance = gdal.getDataInfos(self.datasource[2]['file'], extent, str(self.filter))
            elif self.datasource[0] == 'postgis':
                featCount = postgre.getDataInfos(self.datasource[2], extent, str(self.filter))
            text = text + 'Extent: \n'
            text = text + str(extent[0]) + ', ' + str(extent[1])+'\n'
            text = text + str(extent[2]) + ', ' + str(extent[3])+'\n'
            text = text + str(extent_geo[0]) + ', ' + str(extent_geo[1])+'\n'
            text = text + str(extent_geo[2]) + ', ' + str(extent_geo[3])+'\n'
           
            text = text +'Features:'+ str(featCount)+' \n'
            
            if inner_distance != -1:
                text = text +'Minimum Distance (inner distance): %s\n'%(inner_distance)
            text = text +'Contacted: \n'
            text = text +'...\n'
            text_array.append(text)
           
        self.setTextviews(text_array)  
       
        
    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_geom_info.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_geom_info.get_label())
            self.window.show_all()
            self.closed = False
            
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_geom_info.set_label(self.main_window.ui.mnu_geom_info.get_label().split(self.main_window.menuItemIndicator)[1])
            self.window.hide()
            self.closed = True
            
    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_geom_info.set_label(self.main_window.ui.mnu_geom_info.get_label().split(self.main_window.menuItemIndicator)[1])
    
            
###Listeners
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
###Functions

    def getStatus(self):
        return self.closed
        
    
    
    def setTextviews(self, content):
        
        if len(content) == 9:
            self.textview1.get_buffer().insert(self.textview1.get_buffer().get_end_iter(),content[0])    
            self.textview2.get_buffer().insert(self.textview2.get_buffer().get_end_iter(),content[1])    
            self.textview3.get_buffer().insert(self.textview3.get_buffer().get_end_iter(),content[2])    
            self.textview4.get_buffer().insert(self.textview4.get_buffer().get_end_iter(),content[3])    
            self.textview5.get_buffer().insert(self.textview5.get_buffer().get_end_iter(),content[4])    
            self.textview6.get_buffer().insert(self.textview6.get_buffer().get_end_iter(),content[5])    
            self.textview7.get_buffer().insert(self.textview7.get_buffer().get_end_iter(),content[6])    
            self.textview8.get_buffer().insert(self.textview8.get_buffer().get_end_iter(),content[7])    
            self.textview9.get_buffer().insert(self.textview9.get_buffer().get_end_iter(),content[8]) 
            
        else:
            self.textview1.get_buffer().set_text('')    
            self.textview2.get_buffer().set_text('')    
            self.textview3.get_buffer().set_text('')    
            self.textview4.get_buffer().set_text('')    
            self.textview5.get_buffer().set_text('')    
            self.textview6.get_buffer().set_text('')    
            self.textview7.get_buffer().set_text('')    
            self.textview8.get_buffer().set_text('')    
            self.textview9.get_buffer().set_text('') 