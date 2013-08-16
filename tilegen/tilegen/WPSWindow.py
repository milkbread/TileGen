from gi.repository import Gtk
import mapnik
import time
import os
from multiprocessing import Pool

from tilegen import rendering
from tilegen import WPScommunication as WPScom
from tilegen import gdal_functions as gdal
from tilegen import postgreFunctions
from tilegen import xmlFunctions
from tilegen import functions


class WPSWindow(Gtk.Window):

    def __init__(self, params, xml_files_folder, main_window, name = "WPSWindow", file = "./data/ui/WPSWindow.glade"):
        self.params = params
        self.xml_files_folder = xml_files_folder
        self.main_window = main_window
                
        #basics for loading a *.glade file
        self.builder = Gtk.Builder()
        self.builder.add_from_file(file)
        self.window = self.builder.get_object(name)
        self.initializeContents()
        
        #This is very necessary for an additional window...it handles the click on the close button of the window
        self.window.connect("delete-event", self.closedThisWindow)
        self.closed = True
        
        self.comboProof = False #used to avoid failures when combobox change is applied because it is filled again
        self.genGeomShowed = False
        self.button_showGen_label = self.button_showGen.get_label()
        
        
###Initializations
    def initializeContents(self):
        self.entry_server = self.builder.get_object('entry_server')
        #initialize the wps-server adress
        #self.entry_server.set_text('http://kartographie.geo.tu-dresden.de/webgen_wps/wps')
        self.entry_server.set_text('http://kartographie.geo.tu-dresden.de/webgen_wps/wps')
        self.label_process = self.builder.get_object('label_process')
        self.label_params = self.builder.get_object('label_params')
        self.label_status = self.builder.get_object('label_status')
        self.button_get = self.builder.get_object('button_get')
        self.button_get.connect("clicked", self.on_button_get_clicked)
        self.button_describe = self.builder.get_object('button_describe')
        self.button_describe.connect("clicked", self.on_button_describe_clicked)
        self.button_generalize = self.builder.get_object('button_generalize')
        self.button_generalize.connect("clicked", self.on_button_generalize_clicked)
        self.comboboxtext_processes = self.builder.get_object('comboboxtext_processes')
        self.comboboxtext_processes.connect("changed", self.on_comboboxtext_processes_changed)
        self.button_writeToDB = self.builder.get_object('button_writeToDB')
        self.button_writeToDB.connect("clicked", self.on_button_writeToDB_clicked)
        self.button_showGen = self.builder.get_object('button_showGen')
        self.button_showGen.connect("clicked", self.on_button_showGen_clicked)
        self.visibilityOfFinalisationButtons(False)
        
        
    def initializeWPSWindow(self, mapnik_map, tile_window, styling_window):
        self.mapnik_map = mapnik_map
        self.tile_window = tile_window
        self.styling_window = styling_window        

    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_geom_trans.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_geom_trans.get_label())
            self.window.show_all()
            self.closed = False
            
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_geom_trans.set_label(self.main_window.ui.mnu_geom_trans.get_label().split(self.main_window.menuItemIndicator)[1])
            self.window.hide()
            self.closed = True
            
    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_geom_trans.set_label(self.main_window.ui.mnu_geom_trans.get_label().split(self.main_window.menuItemIndicator)[1])
    
            
###Listeners
    
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
    #GetCapabilities of the setted wps-server and add informations to combobox
    def on_button_get_clicked(self, widget, data=None):
        self.comboProof = True
        
        self.comboboxtext_processes.remove_all()
        self.all_processes = xmlFunctions.getCapabilities(self.entry_server.get_text() + '?service=WPS&Request=GetCapabilities')
        #print self.all_processes
        for i in xrange(len(self.all_processes[0])):
            #print self.all_processes[0][i]
            self.comboboxtext_processes.append_text(self.all_processes[2][i])            
        self.comboboxtext_processes.set_active(0)
        
        self.comboProof = False
    
    def on_comboboxtext_processes_changed(self, widget, data=None):
        chosen_process = []
        if self.comboProof == False:
            chosen_process.append(self.comboboxtext_processes.get_active_text())#Title
            for i in xrange(len(self.all_processes[0])):
                if self.all_processes[2][i] == chosen_process[0]:
                    chosen_process.append(self.all_processes[1][i])#Abstract
                    chosen_process.append(self.all_processes[0][i])#Identifier
            self.label_process.set_text(chosen_process[1])
            self.chosen_identifier = chosen_process[2]
            
    def on_button_describe_clicked(self, widget, data=None):
        if self.chosen_identifier != '':
            self.all_parameters = xmlFunctions.describeProcess(self.entry_server.get_text() + '?service=WPS&Request=DescribeProcess&Service=WPS&Version=1.0.0&Identifier=' + self.chosen_identifier)
                    
            if len(self.all_parameters[0]) == 1: 
                notice = 'There are no additional paramters'
            else: 
                notice = '"Necessary parameters (with default values)"' 
             
            notice = notice + "\n- " + self.all_parameters[2][0]+':'+self.all_parameters[3][0]
            for i in range(1,len(self.all_parameters[0])):
                notice = notice + "\n- " + self.all_parameters[0][i]+ ' - (' +self.all_parameters[2][i]+ '):' +self.all_parameters[4][i] + ' - (' + self.all_parameters[3][i] + ')'
            self.label_params.set_text(notice)
       
        else:
            self.label_status.set_text('No Process chosen!')
            
    def on_button_generalize_clicked(self, widget, data=None):
        if self.styling_window.comboboxtext_rules.get_active() != -1:
            self.visibilityOfFinalisationButtons(False)
            start = time.time()
            #new_object.setButtonLabel(False)     
            
            tileBunch, maxZoom = self.tile_window.getParameterForGeneralisation()#new_object.getTileBunch(zentral_tile)
            self.tileproj = rendering.GoogleProjection(maxZoom+1)
            extentBunch = []
                       
            text = self.label_params.get_text()
            lines = text.split('\n')
            params = []
            for i in range(2,len(lines)):
                    text = lines[i].split(' - ')
                   #print text
                    text2 = text[1].split(':')
                   #print text2
                    params.append((text[0].replace('- ',''),text2[0].replace('(','').replace(')',''),text2[1]))
           #print params
            
            for tile in tileBunch:
                infos = []
                #infos of the tile that should be processed
                extent, z, extent_geo = self.tile_window.getExtents(tile, self.tileproj)
                infos.append(extent)
                
                #infos for the creation of the valid xml-wps file
                source = self.styling_window.datasource[2]['file']
                filter = self.styling_window.filter
                self.symbol_type = self.styling_window.symbol_type
                self.layerSRS = self.styling_window.layerSRS
                func_ident = self.chosen_identifier
                infos.append(source)
                infos.append(func_ident)
                #informations for sending the valid xml-wps file to the server
                server = self.entry_server.get_text()
                dest_file = "WebGen_WPS_"+str(tile[0])+"_"+str(tile[1])+"_"+str(z)+".xml"
                infos.append(server)
                infos.append(dest_file)
                infos.append(self.xml_files_folder)
                chosen_filter = str(filter)
                infos.append(chosen_filter)
                infos.append(params)
                infos.append(tile)
                infos.append(self.params)
                #store all infos in an array, so it is possible to give that array to the multiprocessing-pool (that just takes one variable)
                extentBunch.append(infos)
            
            self.params.writeToLog('Initiated WPS-Execute-Filecreation with...\n\t...server: %s \n\t...filter: %s \n\t...function: %s \n\t...parameters: %s' %(server, str(chosen_filter), str(func_ident), str(params)))
                
            pool = Pool(processes = 9)
            self.results = pool.map(WPScom.doWPSProcess, extentBunch)
            #print self.results
            #new_object.setButtonLabel(True)
            
            print 'Done!'
            self.button_writeToDB.set_child_visible(True)
        else:
            self.label_status.set_text('Please choose a geometry that should be generalized!')
            
    def on_button_writeToDB_clicked(self, widget):
        self.table_name = 'generalized_line_cache'
        self.writeResultToDB(self.results, self.table_name)
        self.button_showGen.set_child_visible(True)

    def on_button_showGen_clicked(self, widget):
        if self.genGeomShowed == False:
            self.name = 'GeneralizedGeometries'
            self.tile_window.addPreviewOfGeneralizedGeometriesToMap(self.table_name, self.symbol_type, self.layerSRS, self.name)
            self.tile_window.reloadMapView()
            self.button_showGen.set_label("unshow\nresults")
            self.genGeomShowed = True
        elif self.genGeomShowed == True:
            self.mapnik_map.remove_style(self.name)
            self.tile_window.reloadMapView()
            self.genGeomShowed = False
            self.button_showGen.set_label(self.button_showGen_label)
            
    
            
###Functions
    def writeResultToDB(self, results, table_name):
        
        postgreFunctions.makePostgresTable(table_name)
        real_results = []
        print 'Begin Writing'
        for result in results:
            if result[0] != '':
                start_time = time.time()
                #real_results.append(result)
                postgreFunctions.writeToPostgres(result[0], table_name)
                final_time = round(time.time()-start_time, 3)
                av = round(result[1]/final_time,3)
                self.params.writeToLog('Wrote %s with %s %s(s) to DB - it took:%s seconds! --> ca. %s /sec'%(result[0], str(result[1]), str(result[2]), str(final_time), str(av)))
        print 'Done writing'
        
        
            
        #pool = Pool(processes = 9)        
        #pool.map(postgreFunctions.writeToPostgres, real_results)
        
    
        
    def getStatus(self):
        return self.closed
        
    def visibilityOfFinalisationButtons(self, visibility):
        self.button_writeToDB.set_child_visible(visibility)
        self.button_showGen.set_child_visible(visibility)
        
    