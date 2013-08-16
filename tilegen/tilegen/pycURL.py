#!/usr/bin/python

#Author: Ralf Klammer 2012

#good Help: http://www.angryobjects.com/2011/10/15/http-with-python-pycurl-by-example/

#pycURL has to be installed
import pycurl
import os
import cStringIO
import time
from tilegen import functions as func
import sys


#Constants
#*********
global filename
filename = ''
global location 
location = ''
global server
server = '' 

#Funktions
#*********
#wps() sends the request via pycURL to the server 
def wps(url):    
    #open the datafile
    data = open(location+filename).read()
    ##print data
    #set pycURL
    #print url
    c = pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.HTTPHEADER, ["Content-Type: text/xml"])
    c.setopt(pycurl.POSTFIELDS, data)
    
    import StringIO
    b = StringIO.StringIO()
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.MAXREDIRS, 5)
    c.perform()
    #print b.getvalue()
    response = b.getvalue()

    return response
    
def simpleRequest(url):
    buf = cStringIO.StringIO()
 
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEFUNCTION, buf.write)
    c.perform()
     
    response = buf.getvalue()
    buf.close()
    return response

#find() returns a string that is between a tag (2 strings)
def find(string, before, behind):    
    e = string.partition(before)
    f = e[2].partition(behind)
    found = f[0]
    #print f[0]

    return found
#save() writes any content to a file...!not explecitely needed!
def save(filename, content):    
    file = open(filename,"w")
    file.write(content)
    file.close()

def downloadFile(url, fileName):
    ret = os.system('wget ' + url + ' -O ' + fileName)         #--> Example: wget http://kartographie.geo.tu-dresden.de/webgen_wps/data/wps1251673673632574965.xml -O test.xml
    return ret
    

#Main programm
#*********
def main(filenameI, locationI, nameI, serverI):
    global filename
    filename = filenameI
    #print filename
    global location 
    location = locationI
    global server
    server = serverI
    
    print 'Request the WPS-Server via pycURL'

    #send the execute command
    response = wps(server)
    #print response
    
    #find the url of status-xml 
    found = find(response,'statusLocation="','" xmlns:wps')
    status_xml = found
    #print "Status-xml: ", status_xml
    
       
    #read the status-xml
    response = ""
    finished = False
    count = 0
    while finished is False:
        
        try:
    
            #print 'Waiting for finishing...'
            response = simpleRequest(status_xml)#wps(status_xml)
            #print response
            
            found = find(response,'<wps:ProcessAccepted>','</wps:ProcessAccepted>')    
            if  count == 0:
                #print found
                count = count+1
            if found == "Request is in progress...":
                finished = False
            else:
                finished = True
                found = find(response,'<wps:ProcessSucceeded>','</wps:ProcessSucceeded>')
                if found == "Process finished successfully.":
                    x = 0
                    #print found
                else:
                    #func.writeToLog( "Any problem occured while using pycURL!!!")
                    wobj = open(os.getenv("HOME")+ 'log-files/TileGen-pycURL-ERRORresponse.xml')
                    wobj.write( response )
                    wobj.close()
                    
        except:
            found = find(response, '<ows:Exception exceptionCode="','" locator="geom">')
            if found == 'InvalidParameterValue':
                print found
                break
            else:
                finished = False
                print 'An error occured for that process: '+status_xml
                print '...I am going on!'
            
        time.sleep(1)
        
        
    #find the url of resulted xml
    found = find(response,'href="','"/>')
    result_xml = found    
    #print "Response-xml: ",result_xml
    final_response = simpleRequest(result_xml)
    #print final_response

    #download the responding gml-file
    transformedFile = location + "result"+ nameI + '.gml'
    #print transformedFile
    save(transformedFile, final_response)
    #downloadFile(result_xml, transformedFile)
    

    return transformedFile
  
    

    

    
