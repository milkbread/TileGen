###testing the Multiprocessing
import numpy
import time
from multiprocessing import Pool
import os
import ogr

###These functions were used before I found out, that the mapnik.map.layer.datasource-object offers me these informations
def getLayer(style):
    with open(style,'rt') as f:
        tree = xml.parse(f)
    
    layer = []
    type = ''
    for elem in tree.iter(tag = 'Layer'):
        #print elem.attrib['name']
        for part in elem.iter(tag='Parameter'):
            if part.attrib['name'] == 'type':
                type = part.text
            if type == 'shape':
                if part.attrib['name'] == 'file':
                    print part.text
                    layer.append(part.text)
            elif type == 'postgis':
                writeToLog('Postgis is not implemented to "functions.getLayer" yet')
            else:
                writeToLog('Please implement that ('+ type +') special case to "functions.getLayer", it is not done yet!')
    return layer
    
def getExtentFromShape(shapefile):
    #print shapefile
    ds = ogr.Open(shapefile)
    if ds is None:
        func.writeToLog("Open %s failed!!!" %shapefile)
        #sys.exit( 1 )
    else:
        layer = ds.GetLayer(0)
        layer.ResetReading()
                
    return layer.GetExtent()
    
###
    
def takeuptime(ntrials):
    
    #print 'huhui'
    for ii in xrange(ntrials[0]):
        junk = numpy.std(numpy.random.randn(1e5))
    print junk
    return junk
    
import pprocess
def test_multiprocessing():
    
    args = []
    for i in xrange(5):
        arg = (500,2)
        args.append(arg)
    print args
    start_time = time.time()   
    #map(takeuptime, [(500,2), (500,2), (500,2), (500,2)])  #or in form of: [takeuptime(args) for args in [500,500]]
    #print 'single Processing: ', time.time() - start_time

    #start_time = time.time()
    #Source-multiprocessing: http://pastebin.com/iGPs699r and http://www.astrobetter.com/parallel-processing-in-python/
    #pool = Pool(processes=4)
    

    #pool.map(takeuptime, args)

    #print 'parallel Processing: ', time.time() - start_time

    start_time = time.time()
    nproc = 10  # maximum number of simultaneous processes desired
    results = pprocess.Map(limit=nproc, reuse=1)
    parallel_function = results.manage(pprocess.MakeReusable(takeuptime))
    [parallel_function(args2) for args2 in args];  # Start computing things
    print results.results
    
    parallel_results = results[0:10]
    print '2nd parallel Processing: ', time.time() - start_time
    print dir(results)
    print dir(results.results)
    print results.results
    for i in results.results.__iter__():
        print i
    
###Testing Classes

def test(uno, dos='Default'):
    print uno
    print dos

class TestClass:
    global t
    t = ''
    global t2
    t2 = ''
    def __init__(self, iterable, default='Hahhaa'):
        global t 
        t = iterable
        global t2
        t2 = default

    def get(self):
        print t
        return t2
        
class shape:
    destination = './data/media/result.shp'
    if os.system('find ' + destination) == 0:
        cache = destination.split('shp')[0]+'*'    
        os.system('rm ' + cache )
        print "Had to delete" + destination    
    spatialReference = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
    driverName = "ESRI Shapefile"
    dataDriver = ogr.GetDriverByName(driverName)
    if not dataDriver:
        raise GeometryError('Could not load driver: {}'.format(driverName))
    dataSource = dataDriver.CreateDataSource(destination)
    
    fieldDefinitions=None
    if not fieldDefinitions:
            fieldDefinitions = []

    def setLayer(self):
        layerName = os.path.splitext(os.path.basename(self.destination))[0]
        spatialReference = self.get_spatialReference(self.spatialReference)
        geometryType = ogr.wkbPolygon
        layer = self.dataSource.CreateLayer(layerName, spatialReference, geometryType)

        # Make fieldDefinitions in featureDefinition
        for fieldName, fieldType in self.fieldDefinitions:
            layer.CreateField(ogr.FieldDefn(fieldName, fieldType))
        #featureDefinition = layer.GetLayerDefn()

        f = ogr.Feature(feature_def=layer.GetLayerDefn())


    def get_spatialReference(self, proj4):
        #    'Return a SpatialReference from proj4'
        spatialReference = osr.SpatialReference()
        if spatialReference.ImportFromProj4(proj4):
            raise GeometryError('Could not import proj4: {}'.format(proj4))
        return spatialReference
        
###read GML        
def readResultedFile(transformedFile):
    #read the  resulted xml
    response = open(transformedFile).read()

    #extract the points from xml (still in xml format)
    found = pycURL.find(response,'<ica:Feature>','</ica:Feature>')
    features = found
    #print features
    count = features.count('<gml:X>')
    #print count, " points where found"

    cache = features
    i = 0
    xml_coords = []
    while i < count:
        g = cache.partition('<gml:coord>')
        h = g[2].partition('</gml:coord>')
        xml_coords.append(h[0])
        cache = h[2]
        #print xml_coords[i]
        #print h[2]
        i = i+1

    #extract the pure geometric points and save to array
    i = 0
    coords = []
    while i < len(xml_coords):
        coord = []
        found = pycURL.find(xml_coords[i],'<gml:X>','</gml:X>')
        coord.append(float(found))    #Problem: bei Umwandlung werden auf 16Bit gerundet
        found = pycURL.find(xml_coords[i],'<gml:Y>','</gml:Y>')
        coord.append(float(found))
        coords.append( coord )
        #print coords[i]
        i = i+1

    #print "extracted Polygon-geometry: ", coords

    #built an OGC polygon geometry
    #python shapely has to be installed
    #from shapely.geometry import Polygon

    #polygon = Polygon(coords)
    #print polygon
    #print list(polygon.exterior.coords)
