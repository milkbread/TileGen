import xml.etree.ElementTree as xml
import time
import os

def writeToLog(content, logs, init = False):
    #home = os.getenv("HOME")
    #logs = home + '/TileGen/log-files/'
    #if not os.path.isdir(logs):
     #   os.mkdir(logs)
    file = open(logs+'TileGen-log.txt',"a")
    if init == True:
        file.write('\n***********************************************************')
        file.write('\n'+str(time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())))
    file.write("\n"+content)
    file.close()
    

#Function to get all informations of a mapnik stylefile
#these are the main map defintion, all styles and all layers
def getContents(style):
    robj = open(style, 'r')
    found_style = False
    styles = []
    one_style = []    
    found_layer = False
    layer = []
    one_layer = []
    map_definition = []
    for line in robj:
        
        if line.find('<Style name') != -1:
            found_style = True
            for i in xrange(len(one_style)):
                one_style.pop()
        elif line.find('</Style') != -1:
            found_style = False
            one_style.append(line)
            styles.append(one_style)
        elif line.find('<Layer name') != -1:
            found_layer = True
            #print line
            for i in xrange(len(one_layer)):
                one_layer.pop()
        elif line.find('Map') != -1:
            map_definition.append(line)
            
        elif line.find('</Layer') != -1:
            found_layer = False
            one_layer.append(line)
            layer.append(one_layer)
        if found_style == True:
            one_style.append(line)
        elif found_layer == True:
            one_layer.append(line)    
        
    robj.close()
    #print layer
    return styles, layer, map_definition

#Function to extract the shapefile of a mapnik stylefile
#!!!does only work if style file only contains one stylefile!!!
def getShapefile(filename):
    robj = open(filename, "r")
    shape = []
    for line in robj: 
        if line.find('.shp') != -1:
            if line.find('<![CDATA[') != -1:
                shape.append(line.split('<![CDATA[')[1].split(']]>')[0])
            else:
                shape.append(line.split('name="file">')[1].split('</Parameter>')[0])
            #print shape
    robj.close()
    return shape
    
    
    
###Old Function

#Function for getting the zentral value of a list of values
#In this case it is related to find the zentral tile of a set of tiles
def getZentralTile(x, y):
    zentral_tile = []
    #X    
    if len(x) % 2 == 0:
        zentral_tile.append(x[(len(x)/2)])
    else:
        zentral_tile.append(x[int(len(x)/2)])
    #Y
    if len(y) % 2 == 0:
        zentral_tile.append(y[(len(y)/2)])
    else:
        zentral_tile.append(y[int(len(y)/2)])
    return zentral_tile
        
    

