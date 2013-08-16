from gi.repository import Gtk
import mapnik
from tilegen import functions
from tilegen import rendering

class ExtentWindow(Gtk.Window):
    
    def __init__(self, params, preview_image, main_window, name = "extent_window", file = "./data/ui/Toolbars.glade"):
        self.main_params = params
        self.main_window = main_window
                
        #basics for loading a *.glade file
        self.builder = Gtk.Builder()
        self.builder.add_from_file(file)
        self.window = self.builder.get_object(name)
        
        self.initializeContents()
        
        #This is very necessary for an additional window...it handles the click on the close button of the window
        self.window.connect("delete-event", self.closedThisWindow)
        self.closed = True
        self.isMapfileInitialized = False
 
###Initializations 
    def initializeContents(self):
        self.comboboxtext_shape = self.builder.get_object('comboboxtext_shape')
        self.comboboxtext_shape.connect("changed", self.on_comboboxtext_shape_changed)
        self.comboboxtext_postgis = self.builder.get_object('comboboxtext_postgis')
        self.comboboxtext_postgis.connect("changed", self.on_comboboxtext_postgis_changed)
        self.label_srs = self.builder.get_object('label_srs')
        self.label_chosen_extent = self.builder.get_object('label_chosen_extent')
        self.entry_lllo = self.builder.get_object('entry_lllo')
        self.entry_urlo = self.builder.get_object('entry_urlo')
        self.entry_llla = self.builder.get_object('entry_llla')
        self.entry_urla = self.builder.get_object('entry_urla')
        
    def initializeMapfile(self, mapnik_map, mapfile, preview_window_class):
        self.isMapfileInitialized = False
        self.mapnik_map = mapnik_map
        self.mapfile = mapfile
        
        self.comboboxtext_shape.remove_all()
        self.comboboxtext_postgis.remove_all()
        
        self.preview_window_class = preview_window_class
        self.preview_window_class.initImage()
        
        
        self.fillComboboxes()
        #self.showWindow()
        
        self.isMapfileInitialized = True
        
###Window communcations with outter world
    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_extent.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_extent.get_label())
            self.window.show_all()
            self.closed = False
        
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_extent.set_label(self.main_window.ui.mnu_extent.get_label().split(self.main_window.menuItemIndicator)[1])
            self.window.hide()
            self.closed = True
        
    def getStatus(self):
        return self.closed

    def getWindow(self):
        return self.window
        
    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_extent.set_label(self.main_window.ui.mnu_extent.get_label().split(self.main_window.menuItemIndicator)[1])
        
    
    def getExtentFromBoxes(self):
        return self.calculateExtent()
        
    #Perform a simple rendering of a single *.png self.image file
    def showPreview(self, mapfile):
        if self.isMapfileInitialized != False:
            rendering.simpleRendering(self.main_params.getPreviewImage(), mapfile, self.calculateExtent())
            self.preview_window_class.reloadImage()
            self.preview_window_class.showWindow()
            
###Listeners
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed

    #lets user choose a shapefile, which will be taken to automatically get an extent of the data
    def on_comboboxtext_shape_changed(self, widget):
        self.shapeName = self.comboboxtext_shape.get_active_text()  
        for layer in self.mapnik_map.layers.__iter__():
            params = layer.datasource.params()
            if params.get('type') == 'shape' and self.extractFileName(params.get('file')) == self.shapeName:
                self.defineMainParams('shape', self.shapeName)
                self.setExtent(layer)
                self.label_chosen_extent.set_text('Extent of %s datasource: \n%s\n(modifiable)'%(params.get('type'), self.shapeName))
        self.showPreview(self.mapfile)
    
    #lets user choose a table, which will be taken to automatically get an extent of the data
    def on_comboboxtext_postgis_changed(self, widget):
        table = self.comboboxtext_postgis.get_active_text()         
        for layer in self.mapnik_map.layers.__iter__():
            params = layer.datasource.params()
            if params.get('type') == 'postgis':
                content = 'DB: %s\nTable: %s '%(params.get('dbname'), params.get('table'))
                if content == table:
                    self.defineMainParams('postgis', table)
                    self.setExtent(layer)
                    self.label_chosen_extent.set_text('Extent of %s datasource: \n%s\n(modifiable)'%(params.get('type'), content))
        self.showPreview(self.mapfile)
    def defineMainParams(self, type, name):
        self.main_params.setExtentSource(type, name)

###Additional functions
    def setupOnLoadingProject(self, send_params):
        if send_params[0] == 'shape':
            for j in xrange(len(self.all_shapes)):
                if self.all_shapes[j] == send_params[1]:
                    self.comboboxtext_shape.set_active(j)
        elif send_params[0] == 'postgis':
            for j in xrange(len(self.all_tables)):
                if self.all_tables[j] == send_params[1]:
                    self.comboboxtext_postgis.set_active(j)

    def calculateExtent(self):
        c0 = self.prj.forward(mapnik.Coord(float(self.entry_lllo.get_text()),float(self.entry_llla.get_text())))
        c1 = self.prj.forward(mapnik.Coord(float(self.entry_urlo.get_text()),float(self.entry_urla.get_text()))) 
        return (float(c0.x), float(c1.x), float(c0.y), float(c1.y))
        
    def fillComboboxes(self):
        
        #self.m = mapnik.Map(256,256)
        #mapnik.load_map(self.m,mapfile)
        self.prj = mapnik.Projection(self.mapnik_map.srs)
        self.all_shapes = []
        self.all_tables = []
        for layer in self.mapnik_map.layers.__iter__():
            self.params = layer.datasource.params()
            type = self.params.get('type')
            if type == 'shape':
                name = self.extractFileName(self.params.get('file'))
                self.comboboxtext_shape.append_text(name)
                self.label_srs.set_text(layer.srs)
                self.all_shapes.append(name)
            elif type == 'postgis':
                content = 'DB: %s\nTable: %s '%(self.params.get('dbname'), self.params.get('table'))
                self.comboboxtext_postgis.append_text(content)
                self.label_srs.set_text(layer.srs)
                self.all_tables.append(content)
            else:
                self.main_params.writeToLog('Please implement the datasourcetype: ('+ type +') to "TileGenWindow.on_comboboxtext_file_changed", it is not done yet!')
                self.label_srs.set_text('')  
   
    def getAllShapesNTables(self):
        return self.all_shapes, self.all_tables
        
                
    def extractFileName(self, fileString):
        name = fileString.split('/')
        if len(name) < 2:
            name = self.params.get('file').split('\\')
        return name[len(name)-1]
        
    #shows user the extent of chosen datasource in geographical LonLat-Format
    def setExtent(self, chosen_layer):
        try:
            #... of a given shapefile
            #extent = gdal.getExtentFromShape(self.shapefile)
            extent = chosen_layer.datasource.envelope()
            
            #convert extent to geographical coordinates...for displaying them to the user
            c0 = self.prj.inverse(mapnik.Coord(round(extent[0],20),round(extent[1],20)))
            c1 = self.prj.inverse(mapnik.Coord(round(extent[2],20),round(extent[3],20)))            

            #fill the entries with the values of the found extent            
            self.entry_lllo.set_text(str(c0.x))
            self.entry_urlo.set_text(str(c1.x))
            self.entry_llla.set_text(str(c0.y))
            self.entry_urla.set_text(str(c1.y)) 
            
            self.main_params.writeToLog('Extent successfully determined!') 
            self.showTilesButton('True')
            
        except:
            self.main_params.writeToLog('Unable to get extent of shapefile!') 
            self.showTilesButton('False')
            
    def showTilesButton(self, status):
        self.main_window.tileButtonVisibility(status)
            
    
        
    
