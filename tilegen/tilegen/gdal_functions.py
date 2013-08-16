#!/usr/bin/env python
import os
import sys
import ogr
from tilegen import xmlFunctions as xmlFunc
from tilegen import functions as func
import time
    
def makeValidFilter(old_filter):
    filter = old_filter.replace('(', '')
    filter = filter.replace(')', '')
    filter = filter.replace('[', '')
    filter = filter.replace(']', '')
    return filter
    
def getDataInfos(source, tile_extent, filter):
    #print 'I am at openOGR'

    
    #print source
    #prepare the filter, for a SQL-query
    filter = makeValidFilter(filter)
    #sourceName = source.split('/')
    #sourceName = sourceName[len(sourceName)-1].split('.')[0]
    datasource = ogr.Open(source)
    ref_datasource = ogr.Open(source)
    #ogr2ogr -f "ESRI Shapefile" -clipsrc 1368218.8239467188, 6489266.422147293, 1407310.7903451964, 6528358.388545775 -overwrite result.shp lines-vgtl-27-01-12.shp
    #1348672.84074748, 6479493.430547676, 1358445.8323470994, 6489266.422147293
    #command = 'ogr2ogr -f "ESRI Shapefile" -clipsrc '+str(tile_extent[0])+', '+str(tile_extent[1])+', '+str(tile_extent[2])+', '+str(tile_extent[3])+' -overwrite result'+str(tile_extent[0])+str(tile_extent[1])+'.shp '+ source
    #print command
    #os.system(command)
    #print tile_extent
    if datasource is None and source.find('\\') != -1:
            source = source.replace('\\', '')
            datasource = ogr.Open(source)
    if ref_datasource is None and source.find('\\') != -1:
            source = source.replace('\\', '')
            ref_datasource = ogr.Open(source)
    if datasource is None or ref_datasource is None:
        print "Unable to open the shapefile!!!\n"
        #func.writeToLog("Unable to open the file %s" %source)
        #sys.exit( 1 )
    else:
            counter = 0
        #for i in xrange(datasource.GetLayerCount()):
            layer = datasource.GetLayer(0)
            layer.ResetReading()
#            print 'FeatureCount:', layer.GetFeatureCount()
            #make the where statement from the given filterattributes
            if filter == 'true':   
                command = "SELECT * FROM "+ layer.GetName()
            else:
                where_statement = 'WHERE ' + filter  
                command = "SELECT * FROM "+ layer.GetName() + ' ' + where_statement
#            print filter
#            print "The select-statement:", command
#            print tile_extent
#            print layer.GetExtent()
            
            filtered_datasource =  datasource.ExecuteSQL(command)
            #spatial filtering the data in relation to the extent of the processed tile
            layer.SetSpatialFilterRect(tile_extent[0], tile_extent[1], tile_extent[2], tile_extent[3])
            #print layer.GetSpatialRef().ExportToProj4()
#            print 'FeatureCount:', layer.GetFeatureCount()

            ref_layer = ref_datasource.GetLayer(0)
            ref_layer.SetAttributeFilter(filter)		
            ref_layer.SetSpatialFilterRect(tile_extent[0], tile_extent[1], tile_extent[2], tile_extent[3])
            
            featCount = layer.GetFeatureCount()
            inner_distance = -1
            if featCount > 1:
                feature = layer.GetNextFeature()
                while feature is not None:
                    geometry = feature.geometry()
                    ref_feature = ref_layer.GetNextFeature()
                    while ref_feature is not None:
                        ref_geometry = ref_feature.geometry()
                        
                        if geometry.Equal(ref_geometry) == False:
                            dist_cache = geometry.Distance(ref_geometry)
#                            print "dist: ", dist_cache
                            if inner_distance == -1 or inner_distance > dist_cache:
                                inner_distance = dist_cache
#                                print "inner_distance: ", inner_distance
                        
                        
                        ref_feature.Destroy()
                        ref_feature = ref_layer.GetNextFeature()
                    feature.Destroy()
                    feature = layer.GetNextFeature()
                    
            return featCount, round(inner_distance,3)
            


#That is a function that:
#    -reads a shapefile
#    -and fills the geometries to a WebGen-WPS-conform XML(GML) file
#     -the XML-file is also initialized in that function but uses another function (makeWPSxml)
#    --> there are some filterings included:
#            - spatial filter --> to just use data of tile-area
#            - attribute (semantical) filter --> to just use the attributes that should be generalized
#Source: That site was very helpfull: http://nullege.com/codes/show/src%40v%40e%40vectorformats-0.1%40vectorformats%40Formats%40OGR.py/85/ogr.Geometry.AddPoint_2D/python
    
def openOGR(source, func_ident, func_parameters, tile_extent, att_filter, dest_file):
    #print 'I am at openOGR'

    #set the filter
    filter = makeValidFilter(att_filter)

    #open the specified shapefile
    ds = ogr.Open(source)

    #initialize the main object     --> needs the identifier of the function and the directory and name of resulting file
    xmlMaker = xmlFunc.makeWPSxml(func_ident, dest_file)
    #send the input paramater of the function to the makeWPSxml-object     --> meaning the generalization parameters
    for params in func_parameters:
        xmlMaker.addInputParameter(params[0], params[0], params[1], params[2])
    geometry_type = ''
    if ds is None:
        print "Unable to open the shapefile!!!\n"
        #sys.exit( 1 )
    else:

        #sourceName = source.split('/')
        #sourceName = sourceName[len(sourceName)-1].split('.')[0]
        #print "Number of Layers: " + str(ds.GetLayerCount())
        counter = 0
        for i in xrange(ds.GetLayerCount()):
            layer = ds.GetLayer(i)
            layer.ResetReading()
#            print layer.GetExtent()
            sourceName = layer.GetName()

            #attribute filtering the data in relation to the semantic that should be generalized
            #make the where statement from the given filterattributes
            where_statement = 'WHERE '    + filter        
            command = "SELECT * FROM "+ sourceName + ' ' + where_statement
            exe =  ds.ExecuteSQL(command)
#            print "The select-statement:", command
#            print 'FeatureCount:', exe.GetFeatureCount()

            #spatial filtering the data in relation to the extent of the processed tile
#           print tile_extent
            layer.SetSpatialFilterRect(tile_extent[0], tile_extent[1], tile_extent[2], tile_extent[3])
#            print 'FeatureCount:', exe.GetFeatureCount()
            
#            print "Number of Features: " + str(layer.GetFeatureCount())
            
            #set the bounding box of the geometrical data        
            #dummyBox = (1,2,3,4)
            xmlMaker.setBBox(layer.GetExtent())

            feature = layer.GetNextFeature()
#            print layer.GetFeatureCount()
            while feature is not None:
                geom = feature.GetGeometryRef()
                
        
#                print feature.GetField('osm_id')
                geometry = feature.GetGeometryRef()
                #print geometry.GetGeometryType()


                if geometry.GetGeometryType() == ogr.wkbMultiPolygon:
                    #func.writeToLog("MultiPolygon found but not implemented to gdal_functions.py - openOGR!") 
                    for x in xrange(geometry.GetGeometryCount()):
                        #print "loop - geometries"
                        ring = geometry.GetGeometryRef(x)
                        #print str(ring)
                        points = badPointExtruder(str(ring))
                                #print ring.GetPointCount()
                                #points = ring.GetPointCount() ... doesn't work!
                    #    for p in xrange(len(points[0])):
                            #print "loop - points"
                                #would be better...but doesn't work
                                #lon, lat, z = ring.GetPoint(p)
                                #gring.AddPoint_2D(lon, lat)        
                            #print float(points[0][p])
                    
                elif geometry.GetGeometryType() == ogr.wkbPolygon:
                    geometry_type = "Polygon"                                    
                    counter = counter + 1                                    
                    ring = geometry.GetGeometryRef(0)
                    points = ring.GetPointCount()
                    all_points = []
                    for p in xrange(points):
                        lon, lat, z = ring.GetPoint(p)
                        one_point = []
                        one_point.append(lon)
                        one_point.append(lat)
                        all_points.append(one_point)
                    #make a WPS-executable XML-File containing the geometries
                    xmlMaker.addFeature('Polygon', all_points)
                    
                elif geometry.GetGeometryType() == ogr.wkbPoint:
                    #func.writeToLog("Point found but not implemented to gdal_functions.py - openOGR!") 
                    lon, lat, z = geometry.GetPoint()
                
                elif geometry.GetGeometryType() == ogr.wkbMultiPoint:
                    #func.writeToLog("Multipoint found but not implemented to gdal_functions.py - openOGR!") 
                    #points = geometry.GetGeometryCount()
                    points = secondBadPointExtruder(str(geometry))                    
                    for p in xrange(len(points[0])):
                        gring = ogr.Geometry(type=ogr.wkbPoint)
                        gring.AddPoint_2D(float(points[0][p]), float(points[1][p]))
                        geometryN.AddGeometry(gring)    
                    #    lon, lat, z = geometry.GetPoint(p)
                    #    print geometry
                    #geometryN.AddPoint_2D(lon, lat)
    

                elif geometry.GetGeometryType() == ogr.wkbLineString:
                    geometry_type = "LineString"
                    #print counter
                    counter = counter + 1                                    
                    points = geometry.GetPointCount()
                    all_points = []
                    for p in xrange(points):
                        lon, lat, z = geometry.GetPoint(p)
                        #print lon, lat
                        one_point = []
                        #print 'number:',len(all_points)
                        #for j in xrange(len(all_points)):
                            #if lon == all_points[j][0]:
                            #    print 'da isser'
                            #if lat == all_points[j][1]:
                            #    print 'da isser...der Ronny unter den Punkten'
                        one_point.append(lon)
                        one_point.append(lat)
                        all_points.append(one_point)
                    #make a WPS-executable XML-File containing the geometries
                    xmlMaker.addFeature('Linestring', all_points)
                        
                        
                elif geometry.GetGeometryType() == ogr.wkbMultiLineString:
                    #func.writeToLog("MultiLineString found but not implemented to gdal_functions.py - openOGR!") 
                    for y in xrange(geometry.GetGeometryCount()):
                        ring = geometry.GetGeometryRef(y)
                        points = ring.GetPointCount()
                        for p in xrange(points):
                            lon, lat, z = ring.GetPoint(p)

                feature.Destroy()
                feature = layer.GetNextFeature()

    #finish the process of creation
        xmlMaker.createXML()
    return counter, geometry_type

#For any reason, the functions GetPointCount and GetPoint do not work for multipolygons
#therefore I need this function...it gets all points of the rings of a multipolygon                
def badPointExtruder(geometry):
    subs = geometry.split('((')
    subs = subs[1].split('))')    
    subs = subs[0].split(',')
    lon = []
    lat = []
    length = len(subs)
    #print subs
    for i in xrange(length):
        subs2 = subs[i].split(' ')
        #print subs2
        lat.append(subs2[0])
        lon.append(subs2[1])
            
    coords = []
    coords.append(lon)
    coords.append(lat)
    return coords

#same is true for multipoints
def secondBadPointExtruder(geometry):
    subs = geometry.split('(')
    subs = subs[1].split(')')    
    subs = subs[0].split(' ')
    #print subs    
    length = len(subs)
    lon = []
    lat = []
    if length == 2:
        subsLon = subs[0].split(',')
        lon.append(subsLon[0]+'.'+subsLon[1])
        subsLat = subs[1].split(',')
        lat.append(subsLat[0]+'.'+subsLat[1])
    else:
        for i in xrange(length):
            if i == 0:
                subs2 = subs[i].split(',')            
                lon.append(subs2[0]+'.'+subs2[1])
            elif i == length-1:
                subs2 = subs[i].split(',')            
                lat.append(subs2[0]+'.'+subs2[1])
            else:    
                subs2 = subs[i].split(',')
                lat.append(subs2[0]+'.'+subs2[1])
                lon.append(subs2[2]+'.'+subs2[3])
    coords = []
    coords.append(lon)
    coords.append(lat)
    return coords
    


                


