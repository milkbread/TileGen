import mapnik
import os
from tilegen import gdal_functions as gdal
from tilegen import pycURL
from tilegen import functions as func
import sys
import time

#Simple rendering of a single *.png image file
# was called 'complexRun' before version 0.8
def simpleRendering(image, stylesheet, extent):
    mapfile = stylesheet
    map_uri = image
    
    imgx = 256
    imgy = 256

    m = mapnik.Map(imgx,imgy)
    mapnik.load_map(m,mapfile)
    #print 'simple Rendering'
    #print m.layers
    
        
    if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 800:
        bbox = mapnik.Box2d(extent[0],extent[2],extent[1],extent[3])
    else:
        bbox = mapnik.Envelope(extent[0],extent[2],extent[1],extent[3])
    m.zoom_to_box(bbox)
    im = mapnik.Image(imgx,imgy)
    mapnik.render(m, im)
    view = im.view(0,0,imgx,imgy) # x,y,width,height
    view.save(map_uri,'png')

#That function does the tile-rendering-job in a very poor form
#previously the necessary tiles where calculated
#...it knows:
#           - tile_dir: where tiles are stored
#           - mapfile:  mapfile as string
#           - maxZoom:  the max zoomfactor
#           - tile_uri: the complete path and name of the tile that will be processed
#           - x,y:      coordinates, respectively name of tile --> will be calculated to geographical coordinates with the help of special class
#           - z:        current zoomfactor where tile should be rendered for
def pure_tile_rendering(args):
    
        tile_dir = args[0] 
        mapfile = args[1]
        maxZoom = args[2]
        tile_uri = args[3]
        x = args[4]
        y = args[5]
        z = args[6]

        #not needed anymore, as the mapnik.map is sent directly to the function
        m = mapnik.Map(256, 256)
        # Load style XML
        mapnik.load_map_from_string(m, mapfile)
        # Obtain <Map> projection
        prj = mapnik.Projection(m.srs)
        # Projects between tile pixel co-ordinates and LatLong (EPSG:4326)
        tileproj = GoogleProjection(maxZoom+1)

        tile = (x,y)
        #print 'Tile: ', tile
        # Calculate pixel positions of bottom-left & top-right
        p0 = (tile[0] * 256, (tile[1] + 1) * 256)
        p1 = ((tile[0] + 1) * 256, tile[1] * 256)
        # Convert to LatLong (EPSG:4326)
        l0 = tileproj.fromPixelToLL(p0, z)
        l1 = tileproj.fromPixelToLL(p1, z)
        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = prj.forward(mapnik.Coord(l0[0],l0[1]))
        c1 = prj.forward(mapnik.Coord(l1[0],l1[1]))

        #c0, c1 = calcTileCoordinates(tile, z)
        tile_extent = (c0.x,c0.y, c1.x,c1.y)
        
        # Bounding box for the tile
        bbox = mapnik.Envelope(c0.x,c0.y, c1.x,c1.y)
        m.zoom_to_box(bbox)

        # Render image with default Agg renderer
        im = mapnik.Image(m.height, m.width)
        mapnik.render(m, im)
        im.save(tile_uri, 'png256') 
        return m.scale()/0.00028




#This function does only...
#...find the minimal zoomlevel of a given extent - meaning when min. 9 tiles are created for that extent
#...collect all the 'minimal' tiles
#...and return these tiles as list
#This function is originally taken from the mapnik source code and is no creative content of ralf klammer!
#...function was called 'renderTiles' until version 0.8
def calcNecTiles(bbox, tile_dir, minZoom, maxZoom):  
    #print "render_tiles(",bbox, mapfile, tile_dir, minZoom,maxZoom, name,")"
    tms_scheme=False

    gprj = GoogleProjection(maxZoom+1) 
    ll0 = (bbox[0],bbox[3])
    ll1 = (bbox[2],bbox[1])
    #print ll0
    #print ll1
    
    stop = False
    finalTiles = []

    for z in range(minZoom,maxZoom + 1):
        if stop == False:        
        
            all_tiles = []
            px0 = gprj.fromLLtoPixel(ll0,z)    
            px1 = gprj.fromLLtoPixel(ll1,z)
            #print z
            #print px0
            #print px1
            
            zoom = str(z)
            for x in range(int(px0[0]/256.0),int(px1[0]/256.0)+1):
                
                # Validate x co-ordinate
                if (x < 0) or (x >= 2**z):
                    continue
                str_x = str(x)
                for y in range(int(px0[1]/256.0),int(px1[1]/256.0)+1):
                    one_tile = []
                    # Validate x co-ordinate
                    if (y < 0) or (y >= 2**z):
                        continue
                    # flip y to match OSGEO TMS spec
                    if tms_scheme:
                        str_y = str((2**z-1) - y)
                    else:
                        str_y = str(y)
                    tile_uri = tile_dir + zoom #+ '/' + str_x + '/' + str_y + '.png'    
                    one_tile.append(x)
                    one_tile.append(y)                    
                    final_uri = tile_uri
                    final_zoom = z                   
                
                    all_tiles.append(one_tile)
        
        if len(all_tiles) >= 9:
            stop = True
            finalTiles = all_tiles

    return finalTiles, final_zoom
    
#Object for the calculations between tile-coordinates (-names) and LonLat-coordinates
from math import pi,cos,sin,log,exp,atan
DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi

def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a

class GoogleProjection:
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
                
    def fromLLtoPixel(self,ll,zoom,doRound = True):
         d = self.zc[zoom]
         e = d[0] + ll[0] * self.Bc[zoom]
         f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom]
         if doRound == True:
             e = round(e)
             g = round(g)
         return (e,g)
     
    def fromPixelToLL(self,px,zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)

###These are functions to tryNerror within the huge univers of mapnikfunctionalities

def qickTest():
    
    m = mapnik.Map(600,300)
    m.background = mapnik.Color('steelblue')
    s = mapnik.Style()
    r = mapnik.Rule()
    #polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color('#ff00ff'))
    #r.symbols.append(polygon_symbolizer)
    
    line_symbolizer = mapnik.LineSymbolizer(mapnik.Color('rgb(100%,100%,100%)'),0.1)
    r.symbols.append(line_symbolizer)
    s.rules.append(r)
    m.append_style('My Style',s)
    line_symbolizer = mapnik.LineSymbolizer(mapnik.Color('rgb(100%,0%,100%)'),0.5)
    r.symbols.append(line_symbolizer)
    s.rules.append(r)
    m.append_style('My New Style',s)
    ds = mapnik.Shapefile(file = '/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/lines-vgtl-27-01-12.shp')
    layer = mapnik.Layer('world')
    layer.datasource = ds
    layer.styles.append('My Style')
    m.layers.append(layer)
    
    lyr = mapnik.Layer('Generalized geometry from PostGIS')
    lyr.datasource = mapnik.PostGIS(host='localhost',user='gisadmin',password='tinitus',dbname='meingis',table='generalized_line_cache')
    lyr.srs = layer.srs
    lyr.styles.append('My New Style')
    m.layers.append(lyr)

    
    m.zoom_all()
    mapnik.render_to_file(m,'world.png', 'png')
    print "rendered image to 'world.png'"


def testMapnik():
    #Help from Dane Springmeyer: https://gist.github.com/3438657
    
    #print mapnik.mapnik_version_string()
    #mapfile = '/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/vogtland_style_PC-version.xml'
    mapfile = '/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/slippy_vogtland.xml'
    
    imgx = 256
    imgy = 256
        #print dir(imgx)

    m = mapnik.Map(imgx,imgy)
    mapnik.load_map(m,mapfile)
    print mapnik.scale_denominator(m,mapnik.Projection(m.srs).geographic)
    m.zoom_all()
    m.buffer_size = 128
    print '*Number of Layers: ',m.layers.__len__()
    for layer in m.layers.__iter__():
            print layer.name
            #print layer.datasource.params().get('type')
            #print layer.name
            #print layer.datasource
            #print dir(layer.datasource)
            #print dir(layer.datasource.envelope())
            #print layer.datasource.envelope()
            #print layer.datasource.params().as_dict()['type']
            #print layer.datasource.envelope().minx
            #print layer.datasource.envelope().width()
            #desc = layer.datasource.params().as_dict()
            #print desc
            #print layer.srs
            #print layer.datasource.envelope()[0]
            #print dir(layer.datasource.features)
            length = len(layer.datasource.all_features())
     #       if length < 10:
      #          print dir(layer.datasource.all_features())
       #         for feature in layer.datasource.all_features().__iter__():
        #            print dir(feature)
         #           for item in feature.iteritems():
          #              print item
           # print dir(layer.datasource)
            #print layer.datasource.fields()
           
            #print '**Number of Styles: ',len(layer.styles)
            for i in xrange(len(layer.styles)):
                #print layer.styles[i]
                style = m.find_style(layer.styles[i])
                #print '***Number of Rules: ',len(style.rules)
        #        for rule in style.rules.__iter__():
        #            print rule.filter, rule.min_scale, rule.max_scale
        #            for j in xrange(len(rule.symbols)):
                        
         #               symbol = rule.symbols[j]
          #              print symbol
           #             symbol_type = str(symbol).split('.')[2].split(' ')[0]
            #            #print symbol_type
             #           if symbol_type == 'PolygonSymbolizer':
              #              help = 0
               #             #print symbol.fill, symbol.fill_opacity, symbol.gamma
                #        elif symbol_type == 'LineSymbolizer':
                 #           stroke = symbol.stroke
                  #          #print stroke.color, stroke.dash_offset, stroke.gamma, stroke.line_cap, stroke.line_join, stroke.opacity, stroke.width
                   ##     else:
                     #       print 'Please implement the missing types!!!!!'
    ##print mapnik.save_map_to_string(m)
    for plugs in mapnik.DatasourceCache.plugin_names():
        plug_in = ''
        for i in xrange(plugs.__len__()):
            plug_in = plug_in + plugs.__getitem__(i)
        #print plug_in

    ds = mapnik.Shapefile(file='/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/lines.shp')
    #print ds.file()
    #print mapnik.mapnik_version_string()

    #print mapnik.scale_denominator(m,mapnik.Projection(m.srs).geographic)
    #print m.scale()
    #print m.scale()/0.00028
    
#Test for getting the minimal zoomlevel of a given extent
def getMinZoom():
    minZoom = 0
    maxZoom = 18
    bbox = (12.8994180674, 50.3684443673, 12.6214373601, 50.7631024618)
    gprj = GoogleProjection(maxZoom+1) 
    
    for z in range(minZoom,maxZoom + 1):        
    
        ll0 = (bbox[0],bbox[3])
        ll1 = (bbox[2],bbox[1])
        px0 = gprj.fromLLtoPixel(ll0,z)    
        px1 = gprj.fromLLtoPixel(ll1,z)

        #print ll0
        #print px0
        #print 'zoom: ' + str(z)
        tiles = int((px1[0]-px0[0])/256)
        if tiles == 1:
            minZoom = z
            #print tiles
        alltiles = tiles * tiles
        #print 'Die Daten passen, in Zoomstufe '+str(z)+', auf '+str(int(tiles))+' x '+str(int(tiles))+' Tiles - das ergibt insgesamt '+str(int(alltiles))+' Tiles!'

    return minZoom


###Old RenderThread - was use a at first in orientation on original mapnik-given tile-rendering function

#This object performs the rendering of tiles
#once initialized it renders only one tile by calling render_tile
#This Object is taken form the mapnik source code
#it was modified for the on demand tile rendering of tilegen
#therefore it contains additionally the function render_on_demand

class RenderThread:
    def __init__(self, tile_dir, mapfile, maxZoom):
        self.tile_dir = tile_dir
        self.m = mapnik.Map(256, 256)
        # Load style XML
        mapnik.load_map(self.m, mapfile, True)
        # Obtain <Map> projection
        self.prj = mapnik.Projection(self.m.srs)
        # Projects between tile pixel co-ordinates and LatLong (EPSG:4326)
        self.tileproj = GoogleProjection(maxZoom+1)

    def render_tile(self, tile_uri, x, y, z, buffer_size):

        tile = (x,y)
        c0, c1 = self.calcTileCoordinates(tile, z)
        tile_extent = (c0.x,c0.y, c1.x,c1.y)
        #dest_file = "WebGen_WPS_file.xml"
        #folder = "/home/klammer/Software/Quickly/tilegen/data/media/"
        #test = makeWPSfile(tile_extent, folder+dest_file)
        #if test > 0:
        #    sendFile(dest_file, folder)
        
    
        # Bounding box for the tile
        if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 800:
            bbox = mapnik.Box2d(c0.x,c0.y, c1.x,c1.y)
        else:
            bbox = mapnik.Envelope(c0.x,c0.y, c1.x,c1.y)
        render_size = 256
        self.m.resize(render_size, render_size)
        self.m.zoom_to_box(bbox)
        self.m.buffer_size = buffer_size

        # Render image with default Agg renderer
        im = mapnik.Image(render_size, render_size)
        mapnik.render(self.m, im)
        im.save(tile_uri, 'png256')

    #Function for the on-demand rendering of tilegen
    def render_on_demand(self, tile_uri, zoom, zentral_tile, buffer_size):
        rendered_tiles = []
        args = []
        for k in range(-1,2):
            for l in range(-1,2):
                start_time = time.time()
                if not os.path.isdir(tile_uri + '/' + str(zentral_tile[0]+k)):
                    os.mkdir(tile_uri + '/' + str(zentral_tile[0]+k))
                uri = tile_uri + '/' + str(zentral_tile[0]+k) + '/' + str(              zentral_tile[1]+l) + '.png'
#               print uri
                # Submit tile to be rendered
                self.render_tile(uri, zentral_tile[0]+k, zentral_tile[1]+l, zoom, buffer_size)#(tile_uri, x, y, z)
                arg = (uri, zentral_tile[0]+k, zentral_tile[1]+l, zoom, buffer_size)
                args.append(arg)
                rendered_tiles.append(uri)    
                #print self.m.scale()/0.00028
            
        #pool = Pool(processes = 4)
        #pool.imap(self.render_tile2, args)
        return rendered_tiles

    def reload_mapfile(self, new_mapfile):
        mapnik.load_map(self.m, new_mapfile, True)

    def calcTileCoordinates(self, tile, zoom):
        # Calculate pixel positions of bottom-left & top-right
        p0 = (tile[0] * 256, (tile[1] + 1) * 256)
        p1 = ((tile[0] + 1) * 256, tile[1] * 256)
        # Convert to LatLong (EPSG:4326)
        l0 = self.tileproj.fromPixelToLL(p0, zoom)
        l1 = self.tileproj.fromPixelToLL(p1, zoom)
        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = self.prj.forward(mapnik.Coord(l0[0],l0[1]))
        c1 = self.prj.forward(mapnik.Coord(l1[0],l1[1]))

        return c0, c1

    def closeWriter(self):
        self.wobj.close()