import xml.etree.ElementTree as xml
from xml.dom import minidom
import cStringIO
import pycurl
import os
from tilegen import functions as func
import mapnik

def getDatasourceFromString(string,chosen_layer):
        print 'Chosen layer: ' + chosen_layer
        m = mapnik.Map(256,256)
        mapnik.load_map_from_string(m,string)
        for layer in m.layers.__iter__():
            if layer.name == chosen_layer:
                params = layer.datasource.params()
                type = params.get('type')
                contents = {}
                contents['type'] = type
                #print type
                if type == 'shape':
                    datasource = params.get('file')
                    if datasource.find('..') != -1:
                        print "Correct datasource related to: '../'"
                        cache = datasource.split('..')
                        datasource = ""
                        cache[0] = cache[0].split('/')
                        for u in range(1, len(cache[0])-2):
                            datasource = datasource +"/"+ cache[0][u]
                        datasource = datasource + cache[1]
                        #print datasource
                    if datasource.find(' ') != -1:
                        datasource = datasource.replace(' ', '\\ ')
                    if datasource.find('-') != -1:
                        replaced_datasource = datasource.replace('-', '_')
                        exists = os.path.isfile(replaced_datasource)
                        if exists == False:
                            command = "ogr2ogr -f 'ESRI Shapefile' "+ replaced_datasource +" " + datasource +" -overwrite"
                            test = os.system(command)
                         #   func.writeToLog('%s is no valid name for processing with ogr!!!' %datasource)
                          #  if test == 0:
                          #      func.writeToLog('It was necessary to rename and copy "%s" to: "%s"' %(datasource, replaced_datasource))
                          #  else:
                          #      func.writeToLog('It was NOT possible to process following command: ', command)
                            
                        datasource = replaced_datasource
                    contents['file'] = datasource
                elif type == 'postgis':
                    content = 'DB: %s\nTable: %s '%(params.get('dbname'), params.get('table'))
                    contents['dbname'] = params.get('dbname')
                    contents['table'] = params.get('table')
                    contents['host'] = params.get('host')
                    contents['port'] = params.get('port')
                    contents['user'] = params.get('user')
                    contents['password'] = params.get('password')
                else:
                    print 'Please implement that ('+ type +') special case!!!'
        """
        response = xml.fromstring(string)
        tree = xml.ElementTree(response)
        datasource = ''
        type = ''
        for elem in tree.iter(tag = 'Layer'):
            if elem.attrib['name'] == chosen_layer:
                #print elem.attrib['name']
                for part in elem.iter(tag='Parameter'):                    
                    if part.attrib['name'] == 'type':
                        type = part.text
                for part in elem.iter(tag='Parameter'):
                    if type == 'shape':
                           #print part.attrib
                           if part.attrib['name'] == 'file':
                               datasource = part.text
                    elif type == 'postgis':
                            print 'Postgis is not implemented yet'
                    else:
                            print 'Please implement that ('+ type +') special case!!!'
                            
        # ogr2ogr -f 'ESRI Shapefile' lines_vgtl_27_01_12.shp lines-vgtl-27-01-12.shp
        """
                            
        #ogr has problems in reading '-'-characters
        #so we have to copy the source with clean name
        
        
        #print contents    
        return contents
        
###Functions for the communication with WPS-Server
###maybe it is not generic enough and too explecitely written for WebGen-WPS

def usecURL(url):
    #print 'cURL-Request: '+url
    buf = cStringIO.StringIO()     
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEFUNCTION, buf.write)
    c.perform()
    response = buf.getvalue()
    #print response
    buf.close()

    return response

def describeProcess(url):
    resp = usecURL(url)
    response = xml.fromstring(resp)
    tree = xml.ElementTree(response)

    all_identifier = []
    all_title = []
    all_abstract = []
    all_type = []
    all_default = []
    all_parameters = []    
    for elem in tree.iter(tag = 'Input'):
        for part in elem.iter():            
            #print part.tag, part.text
            if part.tag == '{http://www.opengis.net/ows/1.1}Identifier':
                all_identifier.append(part.text)
            elif part.tag == '{http://www.opengis.net/ows/1.1}Title':
                all_title.append(part.text)
            elif part.tag == '{http://www.opengis.net/ows/1.1}Abstract':
                all_abstract.append(part.text)
            elif part.tag == 'ComplexData':
                for part2 in part.iter(tag='Format'):
                    shema = part2.find('Schema').text
                all_type.append(shema)
                all_default.append('None')
            elif part.tag == '{http://www.opengis.net/ows/1.1}DataType':
                all_type.append(part.text)
            elif part.tag == 'DefaultValue':
                all_default.append(part.text)
    all_parameters.append(all_identifier)
    all_parameters.append(all_title)
    all_parameters.append(all_abstract)
    all_parameters.append(all_type)
    all_parameters.append(all_default)

    return all_parameters

def getCapabilities(url):
    resp = usecURL(url)
    response = xml.fromstring(resp)
    tree = xml.ElementTree(response)
    
    all_identifier = []
    all_abstracts = []
    all_title = []
    all_processes = []
    for elem in tree.iter(tag='{http://www.opengis.net/wps/1.0.0}Process'):
        #for part in elem.iter():            
            #print part.tag, part.text
        ident = elem.find('{http://www.opengis.net/ows/1.1}Identifier')
        all_identifier.append(ident.text)
        abstract = elem.find('{http://www.opengis.net/ows/1.1}Abstract')
        all_abstracts.append(abstract.text)
        title = elem.find('{http://www.opengis.net/ows/1.1}Title')
        all_title.append(title.text)
    all_processes.append(all_identifier)
    all_processes.append(all_abstracts)
    all_processes.append(all_title)

    return all_processes

#Object to make a xml file that can be sent to the WebGen-WPS
#containing informations about:
#                - the main execute comman
#                - identification of function, that WebGen should call
#                - the geometrical data, that should be generalized
#                - the form of response
class makeWPSxml:
    
    #initialize object
    def __init__(self, identifier, fileName):
        self.filename = fileName

        #initialize the main root object
        self.execute = xml.Element('ns:Execute')
        self.execute.attrib['service'] = 'WPS'
        self.execute.attrib['version'] = '1.0.0'
        #set the namespace of root object
        self.execute.set("xmlns:ns", "http://www.opengis.net/wps/1.0.0")

        #initialize the 1st child "Identifier" --> contains function, that WebGen should call
        #+++needs the identifier, while initializing this object+++
        self.setFunction(identifier)

        #initialize the 2nd child "DataInputs" --> contains Parameters of generalization and the geometrical data
        self.inputs = xml.Element('ns:DataInputs')
        self.execute.append(self.inputs)

        #send the input paramater to the object     --> meaning the generalization parameters
#            identifier = 'minlength'
#            title = 'minlength'
#            abstract = 'minimum length'
#            parameter = str(10.0)
#        self.addInputParameter(identifier, title, abstract, parameter)
        
        #initialize the input of the geometrical data
        #...when multiple layers should be implemented this function should be initialized from 'outside'!!!        
        self.initializeDataInput()

        #initialize the form of response
        #...now working with default parameter --> modifications make steering from 'outside' possible
        self.setResponse()

    def setFunction(self, identifier):
        self.wpsFunction = xml.Element('ns1:Identifier')
        self.wpsFunction.set('xmlns:ns1', 'http://www.opengis.net/ows/1.1')
        self.wpsFunction.text = identifier        
        self.execute.append(self.wpsFunction)

    def addInputParameter(self, identifier, title_content, abstract_content, parameter):
        
        input = xml.Element('ns:Input')
        self.inputs.append(input)
        identif = xml.Element('ns1:Identifier')
        identif.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        identif.text = identifier
        title = xml.Element('ns1:Title')
        title.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        title.text = title_content
        abstract = xml.Element('ns1:Abstract')
        abstract.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        abstract.text = abstract_content
        input.append(identif)
        input.append(title)
        input.append(abstract)
        data = xml.Element('ns:Data')
        input.append(data)

        literalData = xml.Element('ns:LiteralData')
        literalData.text = parameter 
        data.append(literalData)

    def initializeDataInput(self):
        input = xml.Element('ns:Input')
        self.inputs.append(input)
        identif = xml.Element('ns1:Identifier')
        identif.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        identif.text = 'geom'
        title = xml.Element('ns1:Title')
        title.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        title.text = 'geom'
        abstract = xml.Element('ns1:Abstract')
        abstract.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        abstract.text = 'layer with geometries'
        input.append(identif)
        input.append(title)
        input.append(abstract)        

        data = xml.Element('ns:Data')
        input.append(data)

        complexData = xml.Element('ns:ComplexData')
        data.append(complexData)
        self.featureCollection = xml.Element('wps:FeatureCollection')
        self.featureCollection.set('xmlns:wps', "www.icaci.org/genmr/wps")
        complexData.append(self.featureCollection)
        boundedBy = xml.Element('gml:boundedBy')
        boundedBy.set('xmlns:gml', "http://www.opengis.net/gml")
        self.featureCollection.append(boundedBy)
        self.box = xml.Element('gml:Box')
        boundedBy.append(self.box)
    
    def setBBox(self, bbox):
        for i in range(0,2):        
            coord = xml.Element('gml:coord')                                    
            x = xml.Element('gml:X')
            x.text = str(bbox[i])
            coord.append(x)
            y = xml.Element('gml:Y')
            y.text = str(bbox[i+2])
            coord.append(y)
            self.box.append(coord)
            

    def setResponse(self, lineage = 'false', storeE = 'true', status = 'false',asRef = 'true', identifier = 'result', title0 = 'result', abstr = 'generalized geometries'):
        response = xml.Element('ns:ResponseForm')
        self.execute.append(response)
        responseDoc = xml.Element('ns:ResponseDocument')
        responseDoc.attrib['lineage'] = lineage
        responseDoc.attrib['storeExecuteResponse'] = storeE
        responseDoc.attrib['status'] = status
        response.append(responseDoc)
        output = xml.Element('ns:Output')
        output.attrib['asReference'] = asRef
        output.attrib['mimeType'] = 'text/xml'
        output.attrib['encoding'] = 'UTF-8'
        responseDoc.append(output)

        identif = xml.Element('ns1:Identifier')
        identif.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        identif.text = identifier
        title = xml.Element('ns1:Title')
        title.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        title.text = title0
        abstract = xml.Element('ns1:Abstract')
        abstract.set('xmlns:ns1','http://www.opengis.net/ows/1.1')
        abstract.text = abstr
        output.append(identif)
        output.append(title)
        output.append(abstract)
    
    def createXML(self):
        #Open a file        
        file = open(self.filename, 'w')
        #Create an ElementTree object from the root element
        xml.ElementTree(self.execute).write(file)
        #this is helpfull to read file in editor
        #tree = xml.ElementTree(self.execute)
        #tree2 = xml.tostring(self.execute)
        #file.write(minidom.parseString(tree2).toprettyxml())

        #Close the file like a good programmer
        file.close()        

    def addFeature(self, geomType, points):
        feature = xml.Element('wps:Feature')
        self.featureCollection.append(feature)
        attribute = xml.Element('wps:AttributeGEOMETRY')
        feature.append(attribute)
        value = xml.Element('wps:Value')
        value.attrib['srsName'] = "0"
        attribute.append(value)
        if geomType == 'Polygon':
            value.attrib['wpstype'] = "AttributeTypeGeometryPolygon"
            outBound = xml.Element('gml:outerBoundaryIs')
            value.append(outBound)
            outBound.set('xmlns:gml',"http://www.opengis.net/gml")
            ring = xml.Element('gml:LinearRing')
            outBound.append(ring)
            
            for i in xrange(len(points)):
                coord = xml.Element('gml:coord')
                ring.append(coord)                
                x = xml.Element('gml:X')
                x.text = str(points[i][0])
                coord.append(x)
                y = xml.Element('gml:Y')
                y.text = str(points[i][1])
                coord.append(y)
        elif geomType == 'Linestring':
            value.attrib['wpstype'] = "AttributeTypeGeometryLineString"
            for i in xrange(len(points)):
                coord = xml.Element('gml:coord')
                coord.set('xmlns:gml','http://www.opengis.net/gml')
                value.append(coord)                
                x = xml.Element('gml:X')
                x.text = str(points[i][0])
                coord.append(x)
                y = xml.Element('gml:Y')
                y.text = str(points[i][1])
                coord.append(y)
                
                
###Old functions from testphase
    
#origins:    http://www.bigfatalien.com/?p=223r
def testing(content):
    root = xml.Element('root')

    #Create a child element
    for i in xrange(5):
        child = xml.Element('child')
        root.append(child)

        #This is how you set an attribute on an element
    
        child.attrib['name'] = "Charlie" + str(i)

    child.attrib['hosendoof'] = "Mache Eier"

    #Now lets write it to an .xml file on the hard drive

    #Open a file
    filename = "/home/ralf/test.xml"
    file = open(filename, 'w')

    #Create an ElementTree object from the root element
    xml.ElementTree(root).write(file)

    #Close the file like a good programmer
    file.close()

    #os.system('gedit ' + filename)
    
def exemplaryWPSxmlCreation():
    #initialize the main object     --> needs the identifier of the function
        identifier = 'Function that will be processed'
        xmlMaker = xmlFunc.makeWPSxml(identifier, "/home/ralf/Software/Quickly/tilegen/data/media/testWPSFile.xml")
        #send the input paramater to the object     --> meaning the generalization parameters
        identifier = "dummy identifier for parameter"
        title = "dummy title for parameter"
        abstract = "dummy abstract for parameter"
        parameter = "dummy parameter"
        xmlMaker.addInputParameter(identifier, title, abstract, parameter)
        #set the bounding box of the geometrical data        
        dummyBox = (1,2,3,4)
        xmlMaker.setBBox(dummyBox)
        #add a geometry to the xml-file
        xmlMaker.addFeature('Polygon', 'hallo')
        xmlMaker.addFeature('Polygon', 'huhuu')        
        #finish the process of creation
        xmlMaker.createXML()
        print 'Done!'

#Function was written to read the result of WebGen-WPS and store it in the GML-Format that ogr produces
#even though ogr is not able to convert the result to ESRI-shp
#so it is not used anymore
def makeGML(file):
    featColl = xml.Element('ogr:FeatureCollection')
    #set the namespace of root object
    featColl.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    featColl.set("xsi:schemaLocation", "http://ogr.maptools.org/ lines.xsd")
    featColl.set("xmlns:ogr", "http://ogr.maptools.org/")
    featColl.set("xmlns:gml", "http://www.opengis.net/gml")
    
    bounded = xml.Element('gml:boundedBy')
    featColl.append(bounded)
    box = xml.Element('gml:Box')
    bounded.append(box)
    coords1 = xml.Element('gml:coord')    
    coords2 = xml.Element('gml:coord')
    box.append(coords1)
    box.append(coords2)
    

    with open(file,'rt') as g:
        in_tree = xml.parse(g)
    counter = 0
    for node in in_tree.iter():
        #get the bbox and save it to the new file
        if node.tag == '{http://www.opengis.net/gml}boundedBy':
            counter = 0                    
            for part in node.iter():
                if part.tag == '{http://www.opengis.net/gml}coord':
                    for subpart in part.iter():                        
                        if subpart.tag  == '{http://www.opengis.net/gml}X':
                            x = xml.Element('gml:X')
                            x.text = str(round(float(subpart.text),3))
                            if counter == 0:  
                                coords1.append(x)
                            else:
                                coords2.append(x)
                        elif subpart.tag  == '{http://www.opengis.net/gml}Y':
                            y = xml.Element('gml:Y')
                            y.text = str(round(float(subpart.text),3))
                            if counter == 0:  
                                coords1.append(y)
                                counter = counter + 1
                            else:
                                coords2.append(y)

    for node in in_tree.iter(tag = '{www.icaci.org/genmr/wps}Feature'):
        featMem = xml.Element('gml:featureMember')
        lines = xml.Element('ogr:lines')
        lines.attrib['fid'] = 'lines.'+str(counter-1)
        featMem.append(lines)
        geom = xml.Element('ogr:geometryProperty')
        lines.append(geom)
        attribute = xml.Element('ogr:osm_id')
        attribute.text = str(counter)
        lines.append(attribute)
        line2 = xml.Element('gml:LineString')
        geom.append(line2)
        coords = xml.Element('gml:coordinates')
        line2.append(coords)
        featColl.append(featMem)
        x = []
        y = []
        for part in node.iter(tag = '{http://www.opengis.net/gml}X'):
            x.append(part.text)
        for part in node.iter(tag = '{http://www.opengis.net/gml}Y'):
            y.append(part.text)
        strin = ''
        for i in xrange(len(x)):
            if i == 0:
                strin = str(round(float(x[i]),3)) + ',' + str(round(float(y[i]),3))
            else:
                strin = strin + ' ' + str(round(float(x[i]),3)) + ',' + str(round(float(y[i]),3))
        coords.text = strin

        counter = counter + 1
                            

    file2 = open('/home/klammer/Software/Quickly/tilegen/data/media/template_ogr_output.gml', 'w')
    
    file2.write('<?xml version="1.0" encoding="utf-8" ?>')
    xml.ElementTree(featColl).write(file2)
    file2.close()
