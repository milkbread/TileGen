from tilegen import functions
from tilegen import pycURL
from tilegen import gdal_functions

import time

###Functions that are used for the communication with WPS-Server
###Most functions are very specific written for WebGen-WPS...so not generic enough

def makeWPSfile(tile_extent, dest_file, source, func_ident, filter, func_params, tile, params):
    
    func_parameters = func_params
    start_time = time.time() 
    #print source, filter, tile_extent
    result, geometry_type = gdal_functions.openOGR(source, func_ident, func_parameters, tile_extent, filter, dest_file) 
    #***log-output
    params.writeToLog('Make WPS-Execute-File for...\n\t...tile: %s \n\t...tile_extent: %s ' %(str(tile), str(tile_extent)))
    params.writeToLog( str(result) + ' ' + geometry_type + '(s) were processed in '+ str(round(time.time()-start_time, 3))  +' seconds!')
    #***
    return result, geometry_type

def sendFile(filename, location, name, server):
    return pycURL.main(filename, location, name, server)
        
        
def doWPSProcess(params):
    #print params
    tile_extent = params[0]
    source = params[1]
    func_ident = params[2]
    server = params[3]
    dest_file = params[4]
    folder = params[5]
    filter = params[6]
    func_params = params[7]
    main_params = params[9]
    
    #make a xml-file, that is valid for the Execute-command of WebGen_WPS
    test, geometry_type = makeWPSfile(tile_extent, folder+dest_file, source, func_ident, filter, func_params, params[8], main_params)
                
    result = ''
    if test > 0:  
        #try to send execute-file to the server until it was successfull
   #     failure = 1
  #      while failure == 1:
           # try:
                name = dest_file.split('WebGen_WPS')[1].split('.')[0]
                start_time = time.time()    
                result = sendFile(dest_file, folder, name, server)
                main_params.writeToLog( 'Processing of: %s with: %s %s(s) took %s seconds!' % (dest_file, test, geometry_type, str(round(time.time()-start_time, 3))))
                
   #             failure = 0
                print 'Success'
 #           except IOError as e:
  #              print "I/O error({0}): {1}".format(e.errno, e.strerror)
   #         except ValueError:
    #            print "Could not convert data to an integer."
     #       except:
      #          print "Unexpected error:", sys.exc_info()[0]
       #         raise
                
    
    return (result, test, geometry_type)   