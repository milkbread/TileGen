# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _
gettext.textdomain('tilegen')

from gi.repository import Gtk # pylint: disable=E0611
import logging
logger = logging.getLogger('tilegen')

from tilegen_lib import Window
from tilegen.AboutTilegenDialog import AboutTilegenDialog
from tilegen.PreferencesTilegenDialog import PreferencesTilegenDialog
from tilegen.TilesDialog import TilesDialog
from tilegen.StyleditDialog import StyleditDialog
from tilegen import gdal_functions as gdal
from tilegen import rendering
from tilegen import postgreFunctions as postgres
from tilegen import rendering
from tilegen import TileObjects as tiling
from tilegen import PreferenceObjects as preferences
#from tilegen import OpenSaveProjects as osPro
import mapnik
from quickly import prompts
from quickly.widgets.dictionary_grid import DictionaryGrid
import glob
import os
import time
import sys
import ogr
import pickle

from tilegen.old_and_test_functions import test_multiprocessing
from tilegen.ExtentWindow import ExtentWindow
from tilegen.TilesWindow import TilesWindow
from tilegen.ToolsWindow import ToolsWindow
from tilegen.PreviewWindow import PreviewWindow 
from tilegen.StylingWindow import StylingWindow 
from tilegen.InfoWindow import InfoWindow 
from tilegen.WPSWindow import WPSWindow 


from tilegen import WPScommunication as WPScom
from multiprocessing import Pool
from tilegen import postgreFunctions    
        
# See tilegen_lib.Window.py for more details about how this class works
class TilegenWindow(Window):
    __gtype_name__ = "TilegenWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(TilegenWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutTilegenDialog
        self.PreferencesDialog = PreferencesTilegenDialog 
        
        ####
        #initialize some global variables
        self.checkbutton_open = False        
        self.shapefile = ''
        
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)    
         
        #initialize all params
        self.params = preferences.FilesNLogs()
        #initialize all definitions
        self.definitions = preferences.Definitions()
        self.menuItemIndicator = self.definitions.getIndicator()
      
        #set the min- & maxzoom and buffer
        self.defineTilingParams()
        
        self.project = preferences.ProjectFile()
        
        #check the installed mapnik version
        if mapnik.mapnik_version() < self.definitions.getMinMapnikVersion()[0]:
            print self.definitions.getMinMapnikVersion()[1]
            self.params.writeToLog(self.definitions.getMinMapnikVersion()[1])
            sys.exit()
        
        self.setProjectTitle()
        self.ui.label_title.set_alignment(0,0)
        self.tileButtonVisibility(False)
        self.initializedMapfile = False
        self.initialLoad = True
        self.reloaded = False
        
        
        
###Listeners
    ####let the user choose a directory that contains one or more mapnik style files
    def on_button_style_clicked(self, widget, data=None): 
        #clean up the combobox
        self.ui.comboboxtext_file.remove_all()
        
        #let the user choose a path with the directory chooser
        response, path = prompts.choose_directory()
        #make certain the user said ok before working
        if response == Gtk.ResponseType.OK:
            self.params.setUserPath(path)
            self.fillCombobox()
        elif response == Gtk.ResponseType.CANCEL:
            self.ui.label_status.set_text("No directory chosen")
            
    def fillCombobox(self):
        #make a list of the supported xml files
        dicts = dict()
        counter = 0
        #iterate through root directory
        for files in glob.glob(self.params.getUserPath() + "*.xml"):
            if files.endswith('.xml'):
                #create a URI in a format gstreamer likes
                file_uri = self.params.getUserPath()
                fileSplit = files.split(self.params.getUserPath())                
                dicts[str(counter)] = fileSplit[1]    
                counter = counter + 1   
        keylist = dicts.keys()
        keylist.sort() 
        list = []
        #fill the combobox with file names
        for key in keylist: 
               #print key, value
               self.ui.comboboxtext_file.append_text(dicts[key])   
               list.append(dicts[key])
            
        self.ui.label_status.set_text("Path of style: %s"%self.params.getUserPath())
        return list
        
    #set style and shape when combobox has changed
    def on_comboboxtext_file_changed(self, widget, data=None):
        if self.ui.comboboxtext_file.get_active_text() != None:
            #get the chosen stylefile
            self.params.setMapfile(self.ui.comboboxtext_file.get_active_text())
            self.mapnik_map = mapnik.Map(256,256)
            mapnik.load_map(self.mapnik_map, self.params.getMapfileHome())
            
            #open style file if user wants to
            if self.checkbutton_open == True:
                os.system(self.definitions.getEditor() + ' --new-window ' + self.params.getMapfileHome())
    
            if self.initialLoad == False:            
                self.destroyWindows()
            else:
                self.initialLoad = False
            self.loadWindows()
            
            self.mapfileInitialized()
            self.tileButtonVisibility(False)
        else:
            if self.reloaded == True:            
                self.destroyWindows()
                self.loadWindows()
                self.reloaded = False
            
    def mapfileInitialized(self):
        
        self.windowClassExtent.initializeMapfile(self.mapnik_map, self.params.getMapfileHome(), self.windowClassPreview)
        self.windowClassExtent.showWindow()
        self.initializedMapfile = True
        if self.windowClassStyling.getStatus() == False:
            print "Style window reloaded"
            self.windowClassStyling.initializeStylingWindow(self.mapnik_map, self.windowClassTiles, self.windowClassInfo)
    
    def on_destroy(self, widget, data=None):
        """Called when the Window is closed."""
        # Clean up code for saving application state should be added here.
        controle = os.system(' rm -rf '+ self.params.getTilesHome())
        self.params.writeToLog('Deleted tile_dir! %s' %controle)
        
        Gtk.main_quit()
        
    def on_button_set_parameters_clicked(self, widget, data=None):
        self.storeTilingParams()
        
    def on_button_show_tiles_clicked(self, widget, data=None):
        
        #initialize the Tiling Parameters - tiling.TilingParams(extent, minZoom, maxZoom, mapnik_map)
        self.tileParams = tiling.TilingParams(self.windowClassExtent.getExtentFromBoxes() , int(self.ui.entry1.get_text()), int(self.ui.entry2.get_text()), self.mapnik_map)
        self.tileParams.setBufferSize(int(self.ui.entry_buffer.get_text()))
        #initialize the Tiles Window and its parameters
        self.windowClassTiles.initializeTilesWindow(self.windowClassStyling, self.windowClassInfo)
        self.windowClassTiles.initializeParameters(self.tileParams, self.params)
        #initialize the Tools Window with the TilesWindow and show it
        self.windowClassTools.initializeTilesWindow(self.windowClassTiles)
        self.windowClassTools.showWindow()
        #close the Preview Window
        self.windowClassPreview.hideWindow()

        
###Listeners and functions for the communicating with the external windows            
    #initialize the external windows
    def loadWindows(self):
        self.openPreviewWindow() 
        self.openExtentWindow()
        self.openTileWindow()
        self.openToolsWindow()
        self.openStylingWindow()
        self.openInfoWindow()
        self.openWPSWindow()
        
    #destroy the external Windows
    def destroyWindows(self):
        self.windowClassExtent.destroyWindow()
        self.windowClassInfo.destroyWindow()
        self.windowClassWPS.destroyWindow()
        self.windowClassPreview.destroyWindow()
        self.windowClassTiles.destroyWindow()
        self.windowClassTools.destroyWindow()
        self.windowClassStyling.destroyWindow()
        
    def on_mnu_new_activate(self, widget, data=None):
        self.reloaded = True
        #clean up the combobox
        self.ui.comboboxtext_file.remove_all()
        #re-initialize the main objects
        self.params = preferences.FilesNLogs()
        self.project = preferences.ProjectFile()
        self.setProjectTitle()
        
    def on_mnu_save_as_activate(self, widget, data=None):
        self.saveProject(True)
        
    def on_mnu_save_activate(self, widget, data=None):
        self.saveProject(self.project.isBlank())
            
    def saveProject(self, open):
        self.storeTilingParams()
        if open == True:
            self.project.saveProjectWindow(self, self.params)
        self.project.saveAsBinary(self.params)
        self.ui.label_status.set_text("Project '%s' was saved!"%self.project.getPureFileName())
        self.params.writeToLog("Project was saved to: %s"%self.project.getProjectFile())
        self.setProjectTitle()
    
    def on_mnu_open_activate(self, widget, data=None):
        result = self.project.openProjectWindow(self, self.params)
        if result == True:
            self.ui.comboboxtext_file.remove_all()
            self.loadAfterOpening()
            self.setProjectTitle()
            
    def loadAfterOpening(self):
            self.params = self.project.loadProject()
            self.defineTilingParams()
            self.ui.label_status.set_text("Project was loaded!")
            self.params.writeToLog("Project was loaded from: %s"%self.project.getProjectFile())
            #load all contents and windows
            if self.params.getUserPath() != '':
                list = self.fillCombobox()
                for i in xrange(len(list)):
                    if list[i] == self.params.getMapfile():
                        self.ui.comboboxtext_file.set_active(i)
                        if self.params.getExtentStatus() == True:
                            self.windowClassExtent.setupOnLoadingProject(self.params.getExtentSource())
       
    #WPS Window
    def openWPSWindow(self):
        self.windowClassWPS = WPSWindow(self.params, self.params.getXMLFilesHome(), self)
    def on_mnu_geom_trans_activate(self, widget, data=None):
        if self.windowClassWPS.getStatus() == True and self.windowClassTiles.getInitializationStatus() == True:
            self.on_openingGeneralisationWindows(2)
        elif self.windowClassWPS.getStatus() == False:
            self.windowClassWPS.hideWindow()        
    #Information Retrieval Window    
    def openInfoWindow(self):
        self.windowClassInfo = InfoWindow(self.params.getLogfilesHome(), self)
    def on_mnu_geom_info_activate(self, widget, data=None):
        if self.windowClassInfo.getStatus() == True and self.windowClassTiles.getInitializationStatus() == True:
            self.on_openingGeneralisationWindows(1)
        elif self.windowClassInfo.getStatus() == False:
            self.windowClassInfo.hideWindow()        
    #Function that opens the Styling Window for WPS or InformationRetrieval
    def on_openingGeneralisationWindows(self, aim): #aim: 1 InfoRetrieveal, 2 WPS
        self.showStylingWindow(aim)
        self.windowClassExtent.hideWindow()
    
    #Styling Window
    def openStylingWindow(self):
        self.windowClassStyling = StylingWindow(self.params.getLogfilesHome(), self)
    def on_mnu_styling_activate(self, widget, data=None):
        if self.windowClassStyling.getStatus() == True:
            self.windowClassStyling.showWindow()
        elif self.windowClassStyling.getStatus() == False:
            self.windowClassStyling.hideWindow() 
    #Function
    def showStylingWindow(self, aim): #aim: 1 InfoRetrieveal, 2 WPS
        if self.initializedMapfile == True:
            self.windowClassStyling.initializeStylingWindow(self.mapnik_map, self.windowClassTiles, self.windowClassInfo, self.windowClassWPS, aim)
            self.windowClassStyling.showWindow()
    
    #Extent Window
    def openExtentWindow(self):
        self.windowClassExtent = ExtentWindow(self.params, self.params.getPreviewImage(), self)
    def on_mnu_extent_activate(self, widget, data=None):
        if self.windowClassExtent.getStatus() == True:
            self.windowClassExtent.showWindow()
        elif self.windowClassExtent.getStatus() == False:
            self.windowClassExtent.hideWindow() 
     
    #Preview Window
    def openPreviewWindow(self):
        self.windowClassPreview = PreviewWindow(self.params.getPreviewImage(), self)
    def on_mnu_preview_activate(self, widget, data=None):
        if self.windowClassPreview.getStatus() == True:
            self.windowClassPreview.showWindow()
        elif self.windowClassPreview.getStatus() == False:
            self.windowClassPreview.hideWindow()
    
    #Tiles Visualisation Window
    def openTileWindow(self):
        self.windowClassTiles = TilesWindow(self.params.getLogfilesHome(), self)
    def on_mnu_tiles_activate(self, widget, data=None):
        if self.windowClassTiles.getStatus() == True:
            self.windowClassTiles.showWindow()
        elif self.windowClassTiles.getStatus() == False:
            self.windowClassTiles.hideWindow() 
     
    #Tools Window
    def openToolsWindow(self):
        self.windowClassTools = ToolsWindow(self.params.getLogfilesHome(), self)
    def on_mnu_tools_activate(self, widget, data=None):
        if self.windowClassTools.getStatus() == True:
            self.windowClassTools.showWindow()
        elif self.windowClassTools.getStatus() == False:
            self.windowClassTools.hideWindow() 
        
    #Export the current mapfile
    def on_mnu_export_mapfile_activate(self, widget, data=None):
        name = 'TileGen-last-mapfile.xml'
        wobj = open(self.params.getLogfilesHome()+name, 'w')
        wobj.write(mapnik.save_map_to_string(self.mapnik_map))
        wobj.close
        self.ui.label_status.set_text("Mapfile '%s' was exported to: \n\t%s" %(name, self.params.getLogfilesHome()))  
   
    #set the Button for showing the tiles in-/visible ... depends on selection of a proper bbox
    def tileButtonVisibility(self, visibility):
        self.ui.button_show_tiles.set_child_visible(visibility)
                
###Additional Functions
    def setProjectTitle(self):
        self.ui.label_title.set_text(self.project.getPureFileName())
        
    def storeTilingParams(self):
        self.params.setZoomRange(self.ui.entry1.get_text(), self.ui.entry2.get_text())
        self.params.setBuffer(self.ui.entry_buffer.get_text())
    
    def defineTilingParams(self):
        #initialize the entry for the zoomlevels for the tile rendering
        self.ui.entry1.set_text(self.params.getZoomRange()[0])
        self.ui.entry2.set_text(self.params.getZoomRange()[1]) 
        #initialize the size of the tile buffer
        self.ui.entry_buffer.set_text(self.params.getBuffer())
  
    #used to evaluate if style file should be opened in editor
    def on_checkbutton_open_toggled(self, widget, data=None):
        if self.checkbutton_open == True:
            self.checkbutton_open = False 
        elif self.checkbutton_open == False:
            self.checkbutton_open = True

###Test- & Old functions
    def on_button_short_clicked(self, widget, data=None):
        self.project.setProjectFile('/home/klammer/TileGen/projectfiles/neuesProjekt2.tgn')
        self.loadAfterOpening()
        self.setProjectTitle()
        
    def on_button_window_clicked(self, widget, data=None):
        TileCalcs = tiling.TileCalculations((11.8722539115, 50.1713213772, 12.584850326, 50.678205265399974),0,18)
        #TileCalcs.printTileRangeParameters(self.params.getGeneralHome(), 'Extent-Tile-Params.txt')
        #print TileCalcs.getAllTilesOfOneZoomlevel(9)
        print TileCalcs.findStartZoomlevel(2,2)

    def on_button_styledit_clicked(self, widget, data=None):
        if self.params.getMapfileHome() != '':
            styler = StyleditDialog(self.params.getMapfileHome())
            result = styler.run() 
            #close the dialog, and check whether to proceed        
            styler.destroy()
            if result != Gtk.ResponseType.OK:
                return 
    
    def on_button_test_clicked(self, widget, data=None):
        print self.project.getProjectFile()
        print self.project.isBlank()
        print self.project.getPureFileName()
        

    def on_button_mapnik_clicked(self, widget, data=None):
        #rendering.testMapnik()
        test_multiprocessing()
        #rendering.qickTest()
        
        
        
            
    
        
