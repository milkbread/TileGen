from gi.repository import Gtk
import mapnik
import time
import os

from tilegen import rendering
from tilegen import functions
from tilegen import TileObjects as tiling

class TilesWindow(Gtk.Window):
    
    def __init__(self, logfiles, main_window, name = "TileWindow", file = "./data/ui/TileWindow.glade"):
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
        self.initialized = False
 
###Initializations 
    def initializeContents(self):
        self.image1 = self.builder.get_object('image1')
        self.image2 = self.builder.get_object('image2')
        self.image3 = self.builder.get_object('image3')
        self.image4 = self.builder.get_object('image4')
        self.image5 = self.builder.get_object('image5')
        self.image6 = self.builder.get_object('image6')
        self.image7 = self.builder.get_object('image7')
        self.image8 = self.builder.get_object('image8')
        self.image9 = self.builder.get_object('image9')
        self.label_scale = self.builder.get_object('label_scale')
        self.label_zoom = self.builder.get_object('label_zoom')
        
    def initializeTilesWindow(self, styling_window, info_window):
        self.styling_window = styling_window
        self.info_window = info_window
        
    def initializeParameters(self, tileParams, params):
        self.tileParams = tileParams
        self.params = params
        
        self.params.writeToLog('TilesWindow was initialized')
        
        #initialize a tiling.TileCalculations Object
        self.TileCalcs = tiling.TileCalculations(self.tileParams.getGeoCodedBbox(), self.tileParams.getMinZoom(),  self.tileParams.getMaxZoom())
        #get the first zoomlevel, where the chosen datasource fits on 9 Tiles
        self.start_zoom = self.TileCalcs.findStartZoomlevel(3,3)
        allX, allY = self.TileCalcs.getAllTilesOfOneZoomlevel(self.start_zoom)
        #...defining the first central tile
        self.TileNav = tiling.TileNavigator(allX, allY, self.start_zoom, self.params.getTilesHome())
        #render the first displayed tiles
        self.finalVisuals()
        #show the initially zoomfactor
        self.defineZoomLabel()
        
        if self.closed == True:
            self.showWindow()
            
        self.initialized = True
        self.styling_window.showPreviewBox(True)
        
###Listeners
    def showWindow(self):
        self.main_window.ui.mnu_tiles.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_tiles.get_label())
        self.window.show_all()
        self.closed = False
        
    def hideWindow(self):
        self.main_window.ui.mnu_tiles.set_label(self.main_window.ui.mnu_tiles.get_label().split(self.main_window.menuItemIndicator)[1])
        self.window.hide()
        self.closed = True

    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_tiles.set_label(self.main_window.ui.mnu_tiles.get_label().split(self.main_window.menuItemIndicator)[1])
            
    def getStatus(self):
        return self.closed
        
    def getInitializationStatus(self):
        return self.initialized
        
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
###Window management
    #displays the rendered tiles
    def show_tiles(self, rendered_tiles):
         
        self.image1.set_from_file(rendered_tiles[0]) 
        self.image2.set_from_file(rendered_tiles[1]) 
        self.image3.set_from_file(rendered_tiles[2]) 
        self.image4.set_from_file(rendered_tiles[3]) 
        self.image5.set_from_file(rendered_tiles[4]) 
        self.image6.set_from_file(rendered_tiles[5]) 
        self.image7.set_from_file(rendered_tiles[6]) 
        self.image8.set_from_file(rendered_tiles[7]) 
        self.image9.set_from_file(rendered_tiles[8])
        
        if self.styling_window.rule_chosen == True and self.info_window.getStatus() == False:
            self.info_window.initializeInfoWindow(self.tileParams.getMapnikMap(), self, self.styling_window)
        
###Functions
    #Functions for InfoWindow
    def getParameterForGeneralisation(self):
        return self.TileCalcs.getTileBunch(self.TileNav.getCentralTile()), self.tileParams.getMaxZoom()
        
    def getExtents(self, tile, tileproj):
            z = self.TileNav.getZoom()
           #print tile
            p0 = (tile[0] * 256, (tile[1] + 1) * 256)
            p1 = ((tile[0] + 1) * 256, tile[1] * 256)
            # Convert to LatLong (EPSG:4326)
            l0 = tileproj.fromPixelToLL(p0, z)
            l1 = tileproj.fromPixelToLL(p1, z)
            # Convert to map projection (e.g. mercator co-ords EPSG:900913)
            extent_geo = (l0[0],l0[1],l1[0],l1[1])
            c0 = self.tileParams.getProjection().forward(mapnik.Coord(l0[0],l0[1]))
            c1 = self.tileParams.getProjection().forward(mapnik.Coord(l1[0],l1[1]))
        
            tile_extent = (c0.x,c0.y, c1.x,c1.y)
            return tile_extent, z, extent_geo
        
    #**********    
    def navigate(self, direction):
        start_time = time.time()        
        self.TileNav.shift(direction)
        self.finalVisuals()
        
    def scaling(self, direction):
        start_time = time.time()        
        self.TileNav.scaling(direction, self.tileParams.getMaxZoom())
        self.defineZoomLabel()
        self.finalVisuals()

    def finalVisuals(self):
        #render the new tiles
        rendered_tiles = self.render_on_demand(self.TileNav.getURI(), self.TileNav.getZoom(), self.TileNav.getCentralTile())
        #show the new tiles
        self.show_tiles(rendered_tiles)
        
    #that function is only a help to be able to switch between 'render_on_demand_as_loop' and 'render_on_demand_as_multiprocessing'
    def render_on_demand(self, tile_uri, zoom, central_tile):
        start_time = time.time()
        result, scale = self.render_on_demand_as_loop(tile_uri, zoom, central_tile)
        self.label_scale.set_text("1 : " + str(int(round(scale,0))))
        #set log-output
        self.params.writeToLog('Render on demand was used - it took:'+str(round(time.time()-start_time, 3)) + ' seconds!')
        self.params.writeToLog('   --> zentral tile:%s & zoomfactor: %s' %(str(central_tile), str(zoom)))
        return result    
        
    def render_on_demand_as_loop(self, tile_uri, zoom, central_tile):
        rendered_tiles = []
        tileBunch = self.TileCalcs.getTileBunch(central_tile)
        for tile in tileBunch:
            if not os.path.isdir(tile_uri + '/' + str(tile[0])):
                os.mkdir(tile_uri + '/' + str(tile[0]))
            uri = tile_uri + '/' + str(tile[0]) + '/' + str(tile[1]) + '.png'
            arg = (self.params.getTilesHome(), mapnik.save_map_to_string(self.tileParams.getMapnikMap()), self.tileParams.getMaxZoom(), uri,tile[0], tile[1], zoom)
            scale = rendering.pure_tile_rendering(arg)
            rendered_tiles.append(uri)
        return rendered_tiles, scale
        
    def getTileBunch(self, central_tile):
        all_tiles = []
        for k in range(-1,2):
            for l in range(-1,2):
                one_tile = []
                one_tile.append(central_tile[0]+k)
                one_tile.append(central_tile[1]+l)
                all_tiles.append(one_tile)
        return all_tiles
        
    def defineZoomLabel(self):
        self.label_zoom.set_text(str(self.TileNav.getZoom()))
            
    def addPreviewToMap(self, name, scaleDenoms, filter, symbol_type, datasource, layerSRS, prevColor):
        s = mapnik.Style()
        r = mapnik.Rule()
        if symbol_type == 'polygon':
            polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color(prevColor))
            r.symbols.append(polygon_symbolizer)
        elif symbol_type == 'line':
            line_symbolizer = mapnik.LineSymbolizer(mapnik.Color(prevColor),3)
            r.symbols.append(line_symbolizer)
#        elif symbol_type == 'text':
 #           t = mapnik.TextSymbolizer('FIELD_NAME', 'DejaVu Sans Book', 10, Color('black'))
  #          t.halo_fill = Color('white')
   #         t.halo_radius = 1
    #        t.label_placement = label_placement.LINE_PLACEMENT
     #       r.symbols.append(line_symbolizer)
        else:
            print symbol_type, 'has to be implemented to preview!!!'
        if filter != None:
            #f = mapnik.Expression("[waterway] != ''") #'Expression' stands for 'Filter' as this will be replaced in Mapnik3
            r.filter = filter#f
            if scaleDenoms != -1:
                r.min_scale = scaleDenoms[0]
                r.max_scale = scaleDenoms[1]
        s.rules.append(r)
        
        proof = self.tileParams.getMapnikMap().append_style(name,s)
        layer = mapnik.Layer('world')
        layer.datasource = datasource[1]
        layer.srs = layerSRS
        layer.styles.append(name)
        self.tileParams.getMapnikMap().layers.append(layer)
        
    def addPreviewOfGeneralizedGeometriesToMap(self, table_name, symbol_type, layerSRS, name):
        genColor = 'rgb(0%,0%,100%)'
        s = mapnik.Style()
        r = mapnik.Rule()
        if symbol_type == 'polygon':
            polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color(genColor))
            r.symbols.append(polygon_symbolizer)
        elif symbol_type == 'line':
            line_symbolizer = mapnik.LineSymbolizer(mapnik.Color(genColor),2)
            r.symbols.append(line_symbolizer)
        else:
            print symbol_type, 'has to be implemented to preview!!!'
        s.rules.append(r)
        self.tileParams.getMapnikMap().append_style(name,s)
        
        lyr = mapnik.Layer('Generalized geometry from PostGIS')
        lyr.datasource = mapnik.PostGIS(host='localhost',user='gisadmin',password='tinitus',dbname='meingis',table='(select geom from '+ table_name +' ) as geometries')
        lyr.srs = layerSRS
        lyr.styles.append(name)
        self.tileParams.getMapnikMap().layers.append(lyr)
        
    def reloadMapView(self):
        self.finalVisuals()
        
        
