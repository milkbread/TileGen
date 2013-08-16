from tilegen import rendering
import os
import mapnik

class TilingParams:
    def __init__(self, extent, minZoom, maxZoom, mapnik_map):
        self.extent = extent
        self.minZoom = minZoom
        self.maxZoom = maxZoom
        self.mapnik_map = mapnik_map
        
    def getExtent(self):
        return self.extent
    def getMinZoom(self):
        return self.minZoom
    def getMaxZoom(self):
        return self.maxZoom
    def getProjection(self):
        return mapnik.Projection(self.mapnik_map.srs)
    def getMapnikMap(self):
        return self.mapnik_map
    def setBufferSize(self, size):
        self.buffer_size = size
        self.mapnik_map.buffer_size = self.buffer_size
    def getBufferSize(self):
        return self.mapnik_map.buffer_size
        
    def getGeoCodedBbox(self):
        prj = self.getProjection()
        c0 = prj.inverse(mapnik.Coord(float(self.extent[0]),float(self.extent[2])))
        c1 = prj.inverse(mapnik.Coord(float(self.extent[1]),float(self.extent[3])))
        return (c0.x, c0.y, c1.x, c1.y)
    

class TileNavigator:
    def __init__(self, x, y, start_zoom, tile_dir):
        self.calculateCentralTile(x, y)
        self.zoom = start_zoom
        self.tile_dir = tile_dir
        
    def scaling(self, direction, maxZoom):
        if direction == 'in':
            if self.getZoom() < int(maxZoom):
                self.increaseZoom()
            self.setCentralTile(((self.getCentralTile()[0]*2)+1,(self.getCentralTile()[1]*2)+1))
        elif direction == 'out':
            self.decreaseZoom()
            self.setCentralTile(((self.getCentralTile()[0]/2),(self.getCentralTile()[1]/2)))
            
    def shift(self, direction):
        if direction == 'right':
            self.setCentralTile([self.getCentralTile()[0]+1, self.getCentralTile()[1]])
        elif direction == 'left':
            self.setCentralTile([self.getCentralTile()[0]-1, self.getCentralTile()[1]])
        elif direction == 'up':
            self.setCentralTile([self.getCentralTile()[0], self.getCentralTile()[1]-1])
        elif direction == 'down':
            self.setCentralTile([self.getCentralTile()[0], self.getCentralTile()[1]+1])
        
    def increaseZoom(self):
        self.zoom = self.zoom + 1
  
    def decreaseZoom(self):
        self.zoom = self.zoom - 1
        
    def getZoom(self):
        return self.zoom
        
    def getURI(self):
        #make dir if it doesn't exist
        if not os.path.isdir(self.tile_dir + str(self.zoom)):
            os.mkdir(self.tile_dir + str(self.zoom))
        return self.tile_dir + str(self.zoom)
  
    def getCentralTile(self):
        return self.central_tile  
        
    def setCentralTile(self, central_tile):
        self.central_tile = central_tile

    #Function for getting the zentral value of a list of values
    #In this case it is related to find the zentral tile of a set of tiles
    def calculateCentralTile(self, x, y):
        central_tile = []
        #X    
        if len(x) % 2 == 0:
            central_tile.append(x[(len(x)/2)])
        else:
            central_tile.append(x[int(len(x)/2)])
        #Y
        if len(y) % 2 == 0:
            central_tile.append(y[(len(y)/2)])
        else:
            central_tile.append(y[int(len(y)/2)])
        self.central_tile = central_tile
        

class TileCalculations:
    def __init__(self, bboxI, minZoomI, maxZoomI):
        global bbox
        bbox = bboxI
        global minZoom
        minZoom = minZoomI
        global maxZoom
        maxZoom = maxZoomI
        self.initialCalculations()
        
    def initialCalculations(self):
        self.params = [bbox, (minZoom, maxZoom)]
        
        gprj = rendering.GoogleProjection(maxZoom+1) 
        ll0 = (bbox[0],bbox[3])
        ll1 = (bbox[2],bbox[1])
        self.all_zoom_params = []
        for z in range(minZoom,maxZoom + 1):
            self.zoom_param = []
            #[0] - Zoomlevel
            self.zoom_param.append(z)
            px0r = gprj.fromLLtoPixel(ll0,z, True)    
            px1r = gprj.fromLLtoPixel(ll1,z, True) 
            #[1] - BBox in Pixelcoordinates (px): (rounded)
            self.zoom_param.append((px0r[0],px0r[1],px1r[0],px1r[1]))
            px0 = gprj.fromLLtoPixel(ll0,z, False)    
            px1 = gprj.fromLLtoPixel(ll1,z, False)  
            #[2] - BBox in Pixelcoordinates (px): (unrounded)
            self.zoom_param.append((px0[0],px0[1],px1[0],px1[1]))
            xCount = round((px1[0]-px0[0]),3)
            yCount = round((px1[1]-px0[1]),3)
            #[3] - Coverage in px
            self.zoom_param.append((xCount, yCount))
            xTiles = xCount/256
            yTiles = yCount/256
            if xTiles < 1:
                xTiles = round(xTiles,3)
            else:
                xTiles = int(xTiles)
            if yTiles < 1:
                yTiles = round(yTiles,3)
            else:
                yTiles = int(yTiles)
            #[4] - Coverage in Number of Tiles
            self.zoom_param.append((xTiles, yTiles))
            
            tile_area = xTiles*yTiles
            #[5] - Total number of Tiles
            self.zoom_param.append(tile_area)
            
            self.all_zoom_params.append(self.zoom_param)
        #add parametes array and descriptions
        self.params.append((self.all_zoom_params, ("Description: \n[0] - Zoomlevel \n[1] - BBox in Pixelcoordinates (px): (rounded)\n[2] - BBox in Pixelcoordinates (px): (unrounded)\n\t--> unrounded pixelcoordinates are used for further calculations\n[3] - Coverage in px\n[4] - Coverage in Number of Tiles\n[5] - Total number of Tiles")))
        self.params.append("Description: \n[0] - base extent\n[1] - Tuple of Zoomrange\n[2] - all zoomlevel related parameters ([0]-params, [1]-description)\n[3] - Description")
        
    def getInitialParams(self):
        return self.params
        
    def getAllTilesOfOneZoomlevel(self, zoomlevel):
        z = zoomlevel
        allX = []
        allY = []                
        for param in self.params[2][0]:
            if param[0] == z:
                for x in range(int(param[1][0]/256.0),int(param[1][2]/256.0)+1):
                    allX.append(x)
                for y in range(int(param[1][1]/256.0),int(param[1][3]/256.0)+1):
                    allY.append(y) 
                break
        return allX, allY
        
    #this function return the smallest zoomlevel, where the initial Extents fits onto the setted Number of Tiles
    def findStartZoomlevel(self, minTilesX, minTilesY):
        for z in range(minZoom, maxZoom+1):
            x, y = self.getAllTilesOfOneZoomlevel(z)
            if len(x) >= minTilesX and len(y) >= minTilesY:
                return z
                
    def getTileBunch(self, central_tile):
        all_tiles = []
        for k in range(-1,2):
            for l in range(-1,2):
                one_tile = []
                one_tile.append(central_tile[0]+k)
                one_tile.append(central_tile[1]+l)
                all_tiles.append(one_tile)
        return all_tiles
        
    def printTileRangeParameters(self, folder, file):
        file = open(folder + file,"w")
        
        file.write("**************************")
        file.write("\nExtent (lonlat): \n%s"%str(self.params[0]))
        file.write("\nMinZoom: %s - MaxZoom: %s"%(self.params[1][0], self.params[1][1]))
        file.write("\n**************************")
        
        for param in self.params[2][0]:
            file.write("\nZoomlevel: %s"%param[0])
            file.write("\nBBox in Pixelcoordinates (px): (rounded) \n"+str(param[1]))
            file.write("\nBBox in Pixelcoordinates (px): (unrounded) \n"+str(param[2]))
            file.write("\n\t--> unrounded pixelcoordinates are used for further calculations")
            file.write("\nThis extent covers (at zoomlevel %s) an area of: \n%s px (horizontal)\n%s px (vertical)"%(str(param[0]),str(param[3][0]),str(param[3][1])))
            file.write("\nTherefore the extent is (at zoomlevel %s) covered by: \n%s Tile(s) (horizontal)\n%s Tile(s) (vertical)"%(str(param[0]),str(param[4][0]),str(param[4][1])))
            file.write("\nThat makes a total number of %s Tile(s)!"%param[5])
            file.write("\n+++++++++++++++++++++++++++++++")
        file.close