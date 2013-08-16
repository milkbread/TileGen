# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk # pylint: disable=E0611

from tilegen_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('tilegen')

from tilegen import rendering
import mapnik as mapnik
from tilegen import functions as func
from tilegen import xmlFunctions as xmlFunc
from tilegen import gdal_functions as gdal
from tilegen import postgreFunctions as postgre
import os

from multiprocessing import Pool, Process
import multiprocessing
import time
import pprocess

import xml.etree.ElementTree as xml

import time
from threading import Thread  


class TilesDialog(Gtk.Dialog):
    __gtype_name__ = "TilesDialog"

    def __new__(cls, sent):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.

        Returns a fully instantiated TilesDialog object.
        """
        #set if the tile-bbox should be displayed
        #very rude functionality...you have to press reload to see bbox
        global showBbox
        showBbox = False
        added = False
        global added
        
        #get the sent informations
        first_split = sent.split('+')[1]
        global tile_parts
        tile_parts = first_split.split(':')
        #print tile_parts 

        #initialization of all sent data
        global mapfile        
        mapfile = tile_parts[1]
        global mapnik_qmap
        mapnik_qmap = mapnik.Map(256, 256)
        mapnik.load_map(mapnik_qmap,mapfile)
                
        global prj
        prj = mapnik.Projection(mapnik_qmap.srs)#mapnik.Projection("+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=6371000 +b=6371000 +units=m +no_defs")
        extent = tile_parts[0].split('(')[1].split(')')[0].split(', ')
        c0 = prj.inverse(mapnik.Coord(float(extent[0]),float(extent[2])))
        c1 = prj.inverse(mapnik.Coord(float(extent[1]),float(extent[3])))
        bbox = (c0.x, c0.y, c1.x, c1.y)
        global tile_dir
        tile_dir = tile_parts[2]
        global maxZoom
        maxZoom = int(tile_parts[4])
        minZoom = int(tile_parts[3])
        global generalHome
        generalHome = tile_parts[5]
        global logs
        logs = tile_parts[6]
        #get the minimal tile view for setted dataset -->minimum means: mind. 9 Tiles are created
        global all_tiles
        all_tiles = rendering.calcNecTiles(bbox, tile_dir, minZoom, maxZoom)
        #save start zoom
        global start_zoom
        start_zoom = all_tiles[0][2]
        #find all x and y names of the necessary tiles and...               
        global x
        x = []
        x.append(all_tiles[0][0])
        global y
        y = []
        y.append(all_tiles[0][1])
        for i in range(1, len(all_tiles)):
            if (all_tiles[i])[0] > (all_tiles[i-1])[0]:
                x.append(all_tiles[i][0])
        #print 'all x: '+str(x)
        for j in range(1,len(x)):
            if (all_tiles[j])[1] > (all_tiles[j-1])[1]:
                y.append(all_tiles[j][1])
        #print 'all y: '+str(y)
        #...get the zentral tile of all possible
        global zentral_tile
        zentral_tile = func.getZentralTile(x,y)
        #initialize the size of the tile buffer
        global buffer_size
        buffer_size = 128
        #render the the central and all 8 surrounding tiles
        global rendered_tiles
        global first_zentral_uri
        first_zentral_uri = all_tiles[0][3]
        zoom = start_zoom

       # c0, c1 = renderer.calcTileCoordinates(zentral_tile, zoom)
        #print 'Coordinates of Tile:',c0, c1
   
        #initialize the zoomfactor, that is relative to the start zoom
        global zoomFactor
        zoomFactor = 0   
        
        builder = get_builder('TilesDialog')
        global new_object
        new_object = builder.get_object('tiles_dialog')
        new_object.finish_initializing(builder)
        return new_object


    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a TilesDialog object with it in order to
        finish initializing the start of the new TilesDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        
        func.writeToLog('TilesDialog was opened and initialized',logs,True)
        
        #initialize the wps-server adress
        self.ui.entry_server.set_text('http://kartographie.geo.tu-dresden.de/webgen_wps/wps')
        
        #set a mapnik.map to get all styleinformations
        self.mapnik_map = mapnik_qmap
        self.mapnik_map.buffer_size = buffer_size
        
        #initial information request of the used style-file to be able to choose a geometry for generalization
        #loop through all layers
        for layer in self.mapnik_map.layers.__iter__():
            self.ui.comboboxtext_layer.append_text(layer.name)        
        
        #render the first displayed tiles
        rendered_tiles = new_object.render_on_demand(first_zentral_uri, start_zoom, zentral_tile)
        #show the initially rendered tiles
        new_object.show_tiles(rendered_tiles)
        #show the initially setted size of the tile buffer
        self.ui.entry_buffer.set_text(str(buffer_size))
        #show the initially zoomfactor
        self.ui.label_zoom.set_text(str(start_zoom))
        #show the initially setted color for the preview
        self.ui.entry_color.set_text('rgb(100%,0%,100%)')
        
        
        self.buttonLabels = []
        
       
         
         
 
###*************************Choosing Geometries*************************### 

    def on_comboboxtext_layer_changed(self, widget, data=None):
        self.ui.comboboxtext_style.remove_all()
        chosen_layer = self.ui.comboboxtext_layer.get_active_text()  
        self.mapnik_styles = [] 
        #find the chosen layer
        for layer in self.mapnik_map.layers.__iter__():
           if chosen_layer == layer.name:
               source_params = xmlFunc.getDatasourceFromString(mapnik.save_map_to_string(self.mapnik_map),chosen_layer)
               type = source_params['type']
               #print type
               if type == 'shape' or type == 'postgis':
                   self.datasource = (source_params['type'], layer.datasource, source_params)
                   self.layerSRS = layer.srs
                   for style in layer.styles:
                       self.mapnik_styles.append(style)
                       self.ui.comboboxtext_style.append_text(style)
               else:
                    print 'Please implement the missing type: %s' %type
                    self.ui.comboboxtext_style.append_text('Layer type: %s ... it is not implemented yet!' %type)
        
   
    def on_comboboxtext_style_changed(self, widget, data=None):
        self.ui.comboboxtext_rules.remove_all()
        self.ui.textview_symbols.get_buffer().set_text('') 
        if self.ui.comboboxtext_style.get_active() != -1 :            
            chosen_style_name = self.ui.comboboxtext_style.get_active_text()
            #print chosen_style_name
            self.chosen_style = self.mapnik_map.find_style(chosen_style_name)
            self.mapnik_rules = []
            #loop through all rules of the chosen style
            if self.chosen_style.rules.__len__() == 0:
                self.ui.comboboxtext_rules.append_text('Style contains no rule!')
            else:  
                for rule in self.chosen_style.rules.__iter__():
                    rule_content = str(rule.filter) +' '+ str(rule.min_scale) +' '+ str(rule.max_scale) 
                    mapnik_symbols = []
                    for symbol in rule.symbols.__iter__():
                        symbol_type = symbol.type()
                        sym_params = {}
                        #print dir(symbol)
                        if symbol_type == 'polygon':
                            polygon_symbolizer = symbol.polygon()
                            
                            sym_params['Fill'] = str(polygon_symbolizer.fill)
                            sym_params['Fill-opacity'] = str(polygon_symbolizer.fill_opacity)
                            sym_params['Gamma'] = str(polygon_symbolizer.gamma)
                            #print symbol.fill, symbol.fill_opacity, symbol.gamma
                            
                        elif symbol_type == 'line':
                            line_symbolizer = symbol.line()
                            stroke = line_symbolizer.stroke
                            sym_params['Color'] = str(stroke.color) 
                            sym_params['Dash-offset'] = str(stroke.dash_offset) 
                            sym_params['Gamma'] = str(stroke.gamma) 
                            sym_params['Line-cap'] = str(stroke.line_cap) 
                            sym_params['Line-join'] = str(stroke.line_join) 
                            sym_params['Opacity'] = str(stroke.opacity) 
                            sym_params['Width'] = str(stroke.width) 
                            
                            #for test in sym_params.keys():
                               #print test, sym_params[test]
                            
                            #print stroke.color, stroke.dash_offset, stroke.gamma, stroke.line_cap, stroke.line_join, stroke.opacity, stroke.width
                        elif symbol_type == 'text':
                            text_symbolizer = symbol.text()
                            print dir(text_symbolizer)
                            sym_params['allow overlap'] = str(text_symbolizer.allow_overlap)
                            sym_params['avoid edges'] = str(text_symbolizer.avoid_edges)
                            sym_params['displacement'] = str(text_symbolizer.displacement)
                            sym_params['force_odd_labels'] = str(text_symbolizer.force_odd_labels)
                            sym_params['format'] = str(text_symbolizer.format)
                            sym_params['minimum_distance'] = str(text_symbolizer.minimum_distance)
                            sym_params['minimum_path_length'] = str(text_symbolizer.minimum_path_length)
                            sym_params['orientation'] = str(text_symbolizer.orientation)
                            print text_symbolizer.name
                            """
                             	allow_overlap
                            avoid_edges
                            displacement
                            force_odd_labels
                            format
                            format_treehas to be implemented to preview!!!
                            horizontal_alignment
                            justify_alignment
                            label_placement
                            label_position_tolerance
                            label_spacing
                            largest_bbox_only
                            maximum_angle_char_delta
                            minimum_distance
                            minimum_padding
                            minimum_path_length
                            orientation
                            text_ratio
                            vertical_alignment
                            wrap_width"""
                        else:
                            print 'Please implement the missing types!!!!!'
                            
                        
                        self.symbol_type = symbol_type  
                            
                            
                        mapnik_symbols.append((symbol, sym_params))
                       #print symbol
                    self.mapnik_rules.append((rule,rule_content,rule.filter, mapnik_symbols, (rule.min_scale, rule.max_scale)))
                    self.ui.comboboxtext_rules.append_text(rule_content)
                    
            #print 'Number of rules: ', len(self.mapnik_rules)
            #print self.mapnik_rules[0]
            self.ui.comboboxtext_rules.set_active(0)
            
        
    def on_comboboxtext_rules_changed(self, widget, data=None):
        self.mapnik_map.remove_style('preview')
        rule_index = self.ui.comboboxtext_rules.get_active()
                        
        if rule_index != -1:
            if self.ui.comboboxtext_rules.get_active_text() != 'Style contains no rule!':
                self.ui.textview_symbols.get_buffer().set_text('') 
                
                rule = self.mapnik_rules[rule_index]
                #print rule
                self.filter = rule[2]
                self.scaleDenoms = rule[4]
                for symbol in rule[3]:
                    symbol_type = symbol[0].type()
                    end_iter = self.ui.textview_symbols.get_buffer().get_end_iter()                 #help: http://ubuntuforums.org/showthread.php?t=426671
                    self.ui.textview_symbols.get_buffer().insert(end_iter,symbol_type + "Symbolizer") 
                    for key in symbol[1].keys():
                        self.ui.textview_symbols.get_buffer().insert(end_iter,"\n"+ key +":" + symbol[1][key]) 
                    
                #only show preview if user wants to
                if self.ui.switch_preview.get_active() == True:
                    #set the preview of chosen geometries
                    new_object.addPreviewToMap('preview')
                    
                    #reload map display
                    zoom = start_zoom + zoomFactor
                    tile_uri = tile_dir + str(zoom)
                    rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
                    new_object.show_tiles(rendered_tiles)
            else:
                    self.ui.label_status.set_text('No processing without any rule!!!')
        else:
                self.ui.label_status.set_text('No rule chosen!')
               
    
    def showParamsOfGeom(self):
        
        if self.ui.comboboxtext_rules.get_active() != -1:
                new_object.setTextviews('') 
            
                tileBunch = new_object.getTileBunch(zentral_tile)
                texte = []
           #print tileBunch
            #try:
                if showBbox == True: postgre.makePostgresTableBbox()
                    
                for tile in tileBunch:
                    infos = []
                    text = 'Tile= x:' + str(tile[0]) + ' | y:'+ str(tile[1]) +'\n'
                    #infos of the tile that should be processed
                    self.tileproj = rendering.GoogleProjection(maxZoom+1)
                    extent, z = new_object.getExtents(tile)
                    
                    if showBbox == True: postgre.writeBBoxToPostgres('555',extent)
                    
                    featCount = 0
                    #print self.datasource[0]
                    #print 'I am at showParamsOfGeom'
                    if self.datasource[0] == 'shape':
                        featCount = gdal.getDataInfos(self.datasource[2]['file'], extent, str(self.filter))
                    elif self.datasource[0] == 'postgis':
                        featCount = postgre.getDataInfos(self.datasource[2], extent, str(self.filter))
                    text = text + 'Extent: \n'
                    text = text + str(extent[0]) + ', ' + str(extent[1])+'\n'
                    text = text + str(extent[2]) + ', ' + str(extent[3])+'\n'
                   
                    text = text +'Features:'+ str(featCount)+' \n'
                    
                    text = text +'Minimum Distance: \n'
                    text = text +'Contacted: \n'
                    text = text +'...\n'
                    texte.append(text)
                   
                new_object.setTextviews(texte)  
                if showBbox == True: 
                    if added == False:
                        added = True
                        global added
                        new_object.addBoxToMap()
                #print mapnik.save_map_to_string(self.mapnik_map)
            #except:
             #  print 'Geometry has to be chosen!'   
            
            
    def setTextviews(self, content):
        
        if len(content) == 9:
            self.ui.textview1.get_buffer().insert(self.ui.textview1.get_buffer().get_end_iter(),content[0])    
            self.ui.textview2.get_buffer().insert(self.ui.textview2.get_buffer().get_end_iter(),content[1])    
            self.ui.textview3.get_buffer().insert(self.ui.textview3.get_buffer().get_end_iter(),content[2])    
            self.ui.textview4.get_buffer().insert(self.ui.textview4.get_buffer().get_end_iter(),content[3])    
            self.ui.textview5.get_buffer().insert(self.ui.textview5.get_buffer().get_end_iter(),content[4])    
            self.ui.textview6.get_buffer().insert(self.ui.textview6.get_buffer().get_end_iter(),content[5])    
            self.ui.textview7.get_buffer().insert(self.ui.textview7.get_buffer().get_end_iter(),content[6])    
            self.ui.textview8.get_buffer().insert(self.ui.textview8.get_buffer().get_end_iter(),content[7])    
            self.ui.textview9.get_buffer().insert(self.ui.textview9.get_buffer().get_end_iter(),content[8]) 
            
        else:
            self.ui.textview1.get_buffer().set_text('')    
            self.ui.textview2.get_buffer().set_text('')    
            self.ui.textview3.get_buffer().set_text('')    
            self.ui.textview4.get_buffer().set_text('')    
            self.ui.textview5.get_buffer().set_text('')    
            self.ui.textview6.get_buffer().set_text('')    
            self.ui.textview7.get_buffer().set_text('')    
            self.ui.textview8.get_buffer().set_text('')    
            self.ui.textview9.get_buffer().set_text('') 
            
    def addPreviewToMap(self, name):
#self.datasource[1]
#self.layerSRS
#self.symbol_type
#self.filter
#self.scaleDenoms

        s = mapnik.Style()
        r = mapnik.Rule()
        prevColor = self.ui.entry_color.get_text()#'rgb(100%,0%,0%)'
        if self.symbol_type == 'polygon':
            polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color(prevColor))
            r.symbols.append(polygon_symbolizer)
        elif self.symbol_type == 'line':
            line_symbolizer = mapnik.LineSymbolizer(mapnik.Color(prevColor),3)
            r.symbols.append(line_symbolizer)
#        elif self.symbol_type == 'text':
 #           t = mapnik.TextSymbolizer('FIELD_NAME', 'DejaVu Sans Book', 10, Color('black'))
  #          t.halo_fill = Color('white')
   #         t.halo_radius = 1
    #        t.label_placement = label_placement.LINE_PLACEMENT
     #       r.symbols.append(line_symbolizer)
        else:
            print self.symbol_type, 'has to be implemented to preview!!!'
        #print "Filtertest: ",self.filter
        if self.filter != None:
            #f = mapnik.Expression("[waterway] != ''") #'Expression' stands for 'Filter' as this will be replaced in Mapnik3
            r.filter = self.filter#f
            r.min_scale = self.scaleDenoms[0]
            r.max_scale = self.scaleDenoms[1]
        s.rules.append(r)
        
        proof = self.mapnik_map.append_style(name,s)
       #print 'Style appending worked!?: ',proof
        #ds = mapnik.Shapefile(file='/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/lines-vgtl-27-01-12.shp')
        layer = mapnik.Layer('world')
        layer.datasource = self.datasource[1]#ds
        layer.srs = self.layerSRS#self.mapnik_map.srs
        layer.styles.append(name)
        self.mapnik_map.layers.append(layer)
   


        
    
            
        
###*************************Initiating Generalization and Displaying results*************************###  

    #GetCapabilities of the setted wps-server and add informations to combobox
    def on_button_get_clicked(self, widget, data=None):
        self.ui.comboboxtext_processes.remove_all()
        self.all_processes = xmlFunc.getCapabilities(self.ui.entry_server.get_text() + '?service=WPS&Request=GetCapabilities')
        #print self.all_processes
        for i in xrange(len(self.all_processes[0])):
            #print self.all_processes[0][i]
            self.ui.comboboxtext_processes.append_text(self.all_processes[2][i])
            
        self.ui.comboboxtext_processes.set_active(0)
    
    def on_comboboxtext_processes_changed(self, widget, data=None):
        chosen_process = []
        chosen_process.append(self.ui.comboboxtext_processes.get_active_text())#Title
        for i in xrange(len(self.all_processes[0])):
            if self.all_processes[2][i] == chosen_process[0]:
                chosen_process.append(self.all_processes[1][i])#Abstract
                chosen_process.append(self.all_processes[0][i])#Identifier
        self.ui.label_process.set_text(chosen_process[1])
        self.chosen_identifier = chosen_process[2]
            
    def on_button_describe_clicked(self, widget, data=None):
        if self.chosen_identifier != '':
            self.all_parameters = xmlFunc.describeProcess(self.ui.entry_server.get_text() + '?service=WPS&Request=DescribeProcess&Service=WPS&Version=1.0.0&Identifier=' + self.chosen_identifier)
                    
            if len(self.all_parameters[0]) == 1: 
                notice = 'There are no additional paramters'
            else: 
                notice = '"Necessary parameters (with default values)"' 
             
            notice = notice + "\n- " + self.all_parameters[2][0]+':'+self.all_parameters[3][0]
            for i in range(1,len(self.all_parameters[0])):
                notice = notice + "\n- " + self.all_parameters[0][i]+ ' - (' +self.all_parameters[2][i]+ '):' +self.all_parameters[4][i] + ' - (' + self.all_parameters[3][i] + ')'
            self.ui.label_params.set_text(notice)
       
        else:
            self.ui.label_status.set_text('No Process chosen!')
    
    def on_button_generalize_clicked(self, widget, data=None):
        if self.ui.comboboxtext_rules.get_active() != -1:
            start = time.time()
            #new_object.setButtonLabel(False)     
            
            tileBunch = new_object.getTileBunch(zentral_tile)
            self.tileproj = rendering.GoogleProjection(maxZoom+1)
            
            extentBunch = []
            
            text = self.ui.label_params.get_text()
            lines = text.split('\n')
            params = []
            for i in range(2,len(lines)):
                    text = lines[i].split(' - ')
                   #print text
                    text2 = text[1].split(':')
                   #print text2
                    params.append((text[0].replace('- ',''),text2[0].replace('(','').replace(')',''),text2[1]))
           #print params
            
            for tile in tileBunch:
                infos = []
                #infos of the tile that should be processed
                extent, z = new_object.getExtents(tile)
                infos.append(extent)
                #infos for the creation of the valid xml-wps file
                source = self.datasource[2]['file']#"/home/klammer/Software/Quickly/tilegen/data/media/testdaten/mercator_polygon/linesvgtl270112.shp"
                func_ident = self.chosen_identifier#'ch.unizh.geo.webgen.service.LineSmoothing'
                infos.append(source)
                infos.append(func_ident)
                #informations for sending the valid xml-wps file to the server
                server = self.ui.entry_server.get_text()
                dest_file = "WebGen_WPS_"+str(tile[0])+"_"+str(tile[1])+"_"+str(z)+".xml"
                xml_files_folder = generalHome + 'xmlfiles/'
                if not os.path.isdir(xml_files_folder):
                    os.mkdir(xml_files_folder)
        
                #folder = "/home/klammer/Software/Quickly/tilegen/data/media/cache/xmlfiles/"
                infos.append(server)
                infos.append(dest_file)
                infos.append(xml_files_folder)
                chosen_filter = str(self.filter)
                infos.append(chosen_filter)
                infos.append(params)
                infos.append(tile)
                infos.append(logs)
                #store all infos in an array, so it is possible to give that array to the multiprocessing-pool (that just takes one variable)
                extentBunch.append(infos)
                
            func.writeToLog('Initiated WPS-Execute-Filecreation with...\n\t...server: %s \n\t...filter: %s \n\t...function: %s \n\t...parameters: %s' %(server, str(chosen_filter), str(func_ident), str(params)),logs)
            pool = Pool(processes = 9)        
            results = pool.map(rendering.doWPSProcess, extentBunch)
           #print results
            
            #new_object.setButtonLabel(True)
            
            print 'Done!'
            
            postgre.makePostgresTable()
            real_results = []
            for result in results:
                if result != '':
                    #real_results.append(result)
                    postgre.writeToPostgres(result)
                    print 'Writing'
            print 'Done writing'
                
            #pool = Pool(processes = 9)        
            #pool.map(postgre.writeToPostgres, real_results)
            
            self.ui.button_showGen.set_label('Use generalized\ngeometries')
        else:
            self.ui.label_status.set_text('Please choose a geometry that should be generalized!')
        
    def on_button_showGen_clicked(self, widget, data=None):
 #       text1 = 'Use generalized\ngeometries'
  #      text2 = 'Use original\ngeometries'
   #     current_text = self.ui.button_showGen.get_label()
    #    if current_text == text1 or current_text == text2:
     #       if current_text == text1:
      #          self.ui.button_showGen.set_label(text2)
                #self.mapnik_map.remove_style('preview')
                new_object.addGeneralizedToMap('generalized geometries')
                
                #reload map display
                zoom = start_zoom + zoomFactor
                tile_uri = tile_dir + str(zoom)
                rendered_tiles, scale = new_object.render_on_demand_as_loop(tile_uri, zoom, zentral_tile)
                #print rendered_tiles
                new_object.show_tiles(rendered_tiles)
                
 #           elif current_text == text2:
  #              self.ui.button_showGen.set_label(text1)
   #             self.mapnik_map.remove_style('generalized geometries')
    #    else:
     #       self.ui.label_status.set_text('Please generalize some data before displaying them')
            
    def addGeneralizedToMap(self, name='My New Style'):
        genColor = 'rgb(0%,0%,100%)'
        s = mapnik.Style()
        r = mapnik.Rule()
        if self.symbol_type == 'polygon':
            polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color(genColor))
            r.symbols.append(polygon_symbolizer)
        elif self.symbol_type == 'line':
            line_symbolizer = mapnik.LineSymbolizer(mapnik.Color(genColor),2)
            r.symbols.append(line_symbolizer)
        else:
            print self.symbol_type, 'has to be implemented to preview!!!'
        s.rules.append(r)
        self.mapnik_map.append_style(name,s)
        
        lyr = mapnik.Layer('Generalized geometry from PostGIS')
        lyr.datasource = mapnik.PostGIS(host='localhost',user='gisadmin',password='tinitus',dbname='meingis',table='(select geom from generalized_line_cache ) as water_ways')
        lyr.srs = self.layerSRS
        lyr.styles.append(name)
        self.mapnik_map.layers.append(lyr)
        
    def addBoxToMap(self, name='bbox'):
        genColor = 'rgb(0%,0%,100%)'
        s = mapnik.Style()
        r = mapnik.Rule()
        line_symbolizer = mapnik.LineSymbolizer(mapnik.Color(genColor),10)
        r.symbols.append(line_symbolizer)
        s.rules.append(r)
        self.mapnik_map.append_style(name,s)
        
        lyr = mapnik.Layer('BBox')
        lyr.datasource = mapnik.PostGIS(host='localhost',user='gisadmin',password='tinitus',dbname='meingis',table='(select geom from bbox ) as water_ways')
        lyr.srs = self.layerSRS
        lyr.styles.append(name)
        self.mapnik_map.layers.append(lyr)

        
        
###*************************Tile Display and Interactive Elements*************************###                 

    #Go East
    def on_button_right_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        #zoom is relative to start and zoomfactor
        zoom = start_zoom + zoomFactor
        #change the x values for new tiles
        x.append(x[len(x)-1]+1)   
        x.pop(0)
        #set new zentral tile
        global zentral_tile
        zentral_tile = func.getZentralTile(x,y)
        #set tile uri
        tile_uri = tile_dir + str(zoom)
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)
        
    #Go West
    def on_button_left_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        #zoom is relative to start and zoomfactor
        zoom = start_zoom + zoomFactor
        #change the x values for new tiles
        x.insert(0, x[0]-1)
        x.pop(len(x)-1)
        #set new zentral tile
        global zentral_tile
        zentral_tile = func.getZentralTile(x,y)
        #set tile uri
        tile_uri = tile_dir + str(zoom)
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)

    #Go North
    def on_button_up_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        #zoom is relative to start and zoomfactor
        zoom = start_zoom + zoomFactor
        #change the y values for new tiles
        y.insert(0, y[0]-1)
        y.pop(len(y)-1)
        #set new zentral tile
        global zentral_tile
        zentral_tile = func.getZentralTile(x,y)
        #set tile uri
        tile_uri = tile_dir + str(zoom)
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)

    #Go South
    def on_button_down_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        #zoom is relative to start and zoomfactor
        zoom = start_zoom + zoomFactor
        #change the y values for new tiles
        y.append(y[len(y)-1]+1)   
        y.pop(0)
        #set new zentral tile
        global zentral_tile
        zentral_tile = func.getZentralTile(x,y)
        #set tile uri
        tile_uri = tile_dir + str(zoom)
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)

    #Zoom in
    def on_button_zoom_in_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        #zoom is relative to start and zoomfactor...so zoomfactor has to be increased while zooming
        global zoomFactor
        zoomFactor = zoomFactor + 1
        zoom = start_zoom + zoomFactor
        if zoom == 19:
            zoomFactor = zoomFactor - 1
            zoom = start_zoom + zoomFactor
        #set the new zentral tile
        global zentral_tile
        zentral_tile = ((zentral_tile[0]*2)+1,(zentral_tile[1]*2)+1)
        #set the tile uri
        tile_uri = tile_dir + str(zoom)
        #change label to new zoomfactor
        self.ui.label_zoom.set_text(str(zoom))
        #clear all x
        for i in xrange(len(x)):
            x.pop()
        #clear all y
        for i in xrange(len(y)):
            y.pop()
        #fill x and y with new tiles
        for i in range(-1,2):
            x.append(zentral_tile[0]+i)
            y.append(zentral_tile[1]+i)
        #make dir if it does'n exitst
        if not os.path.isdir(tile_dir + str(zoom)):
            os.mkdir(tile_dir + str(zoom))
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)

    #Zoom out
    def on_button_zoom_out_clicked(self, widget, data=None):
        global start_time
        start_time = time.time()        
        
        #zoom is relative to start and zoomfactor...so zoomfactor has to be decreased while zooming
        global zoomFactor
        zoomFactor = zoomFactor - 1
        zoom = start_zoom + zoomFactor
        #set the new zentral tile
        global zentral_tile
        zentral_tile = ((zentral_tile[0]/2),(zentral_tile[1]/2))
        #set the tile uri
        tile_uri = tile_dir + str(zoom)
        #change label to new zoomfactor
        self.ui.label_zoom.set_text(str(zoom))
        #clear all x
        for i in xrange(len(x)):
            x.pop()
        #clear all y
        for i in xrange(len(y)):
            y.pop()
        #fill x and y with new tiles
        for i in range(-1,2):
            x.append(zentral_tile[0]+i)
            y.append(zentral_tile[1]+i)
        #make dir if it does'n exitst
        if not os.path.isdir(tile_dir + str(zoom)):
            os.mkdir(tile_dir + str(zoom))
        #render the new tiles
        global rendered_tiles
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        #show the new tiles
        new_object.show_tiles(rendered_tiles)
        
        
    #Enables user to reload the tiles - e.g. when stylefile was changed
    def on_button_reload_clicked(self, widget, data=None):
        #self.mapnik_map.background = mapnik.Color('steelblue')
        zoom = start_zoom + zoomFactor
        tile_uri = tile_dir + str(zoom)
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        new_object.show_tiles(rendered_tiles)

    #Enables user to define the size of the buffer which is used when rendering each tile
    def on_button_buffer_clicked(self, widget, data=None):
        global buffer_size
        buffer_size = int(self.ui.entry_buffer.get_text())
        self.mapnik_map.buffer_size = buffer_size
        zoom = start_zoom + zoomFactor
        tile_uri = tile_dir + str(zoom)
        rendered_tiles = new_object.render_on_demand(tile_uri, zoom, zentral_tile)
        new_object.show_tiles(rendered_tiles)
        
    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        logs = os.getenv("HOME") + '/TileGen/log-files/'
        wobj = open(logs+'TileGen-last-mapfile.xml', 'w')
        wobj.write(mapnik.save_map_to_string(self.mapnik_map))
        wobj.close
        
        func.writeToLog('Deleted tile_dir! %s' %os.system(' rm -rf '+ tile_dir),logs)
        pass
        
   

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        
        pass

###*************************Additional Functions*************************### 
    #displays the rendered tiles
    def show_tiles(self, rendered_tiles):
         
        new_object.showParamsOfGeom()
        #print rendered_tiles

        self.ui.image1.set_from_file(rendered_tiles[0]) 
        self.ui.image2.set_from_file(rendered_tiles[1]) 
        self.ui.image3.set_from_file(rendered_tiles[2]) 
        self.ui.image4.set_from_file(rendered_tiles[3]) 
        self.ui.image5.set_from_file(rendered_tiles[4]) 
        self.ui.image6.set_from_file(rendered_tiles[5]) 
        self.ui.image7.set_from_file(rendered_tiles[6]) 
        self.ui.image8.set_from_file(rendered_tiles[7]) 
        self.ui.image9.set_from_file(rendered_tiles[8])
                
        
        
    #that function is only a help to be able to switch between 'render_on_demand_as_loop' and 'render_on_demand_as_multiprocessing'
    def render_on_demand(self, tile_uri, zoom, zentral_tile):
        start_time = time.time()
        #result, scale = new_object.render_on_demand_as_multiprocessing(tile_uri, zoom, zentral_tile)
        result, scale = new_object.render_on_demand_as_loop(tile_uri, zoom, zentral_tile)
        self.ui.label_scale.set_text("1 : " + str(int(round(scale,0))))
        #set log-output
        func.writeToLog('Render on demand was used - it took:'+str(round(time.time()-start_time, 3)) + ' seconds!',logs)
        func.writeToLog('   --> zentral tile:%s & zoomfactor: %s' %(str(zentral_tile), str(zoom)),logs)
        return result
    
        
    def render_on_demand_as_loop(self, tile_uri, zoom, zentral_tile):
        rendered_tiles = []
        tileBunch = new_object.getTileBunch(zentral_tile)
        for tile in tileBunch:
            if not os.path.isdir(tile_uri + '/' + str(tile[0])):
                os.mkdir(tile_uri + '/' + str(tile[0]))
            uri = tile_uri + '/' + str(tile[0]) + '/' + str(tile[1]) + '.png'
            arg = (tile_dir, mapnik.save_map_to_string(self.mapnik_map), maxZoom, uri,tile[0], tile[1], zoom)
            scale = rendering.pure_tile_rendering(arg)
            rendered_tiles.append(uri)
        return rendered_tiles, scale
        
    def render_on_demand_as_multiprocessing(self, tile_uri, zoom, zentral_tile):
        rendered_tiles = []
        args = []
        tileBunch = new_object.getTileBunch(zentral_tile)
        for tile in tileBunch:
            if not os.path.isdir(tile_uri + '/' + str(tile[0])):
                os.mkdir(tile_uri + '/' + str(tile[0]))
            uri = tile_uri + '/' + str(tile[0]) + '/' + str(tile[1]) + '.png'
            arg = (tile_dir, mapnik.save_map_to_string(self.mapnik_map), maxZoom, uri,tile[0], tile[1], zoom)
            args.append(arg)
            rendered_tiles.append(uri)
            #Process tile rendering as multiprocessing using internal modul of python 
            #Help: http://www.ibm.com/developerworks/aix/library/au-multiprocessing/
            
            #alternative Multiprocessing...especially when an object (unconvertable to String-format) should be send to function
            #Process(target=rendering.pure_tile_rendering, args=(tile_dir, self.mapnik_map, maxZoom, uri,tile[0], tile[1], zoom)).start()
            #rendered_tiles.append(uri)
        pool = Pool(processes = 9)
        results = pool.map(rendering.pure_tile_rendering, args) 
        
        scale = results[0]
                        
        return rendered_tiles, scale
        
    def getTileBunch(self, zentral_tile):
        all_tiles = []
        for k in range(-1,2):
            for l in range(-1,2):
                one_tile = []
                one_tile.append(zentral_tile[0]+k)
                one_tile.append(zentral_tile[1]+l)
                all_tiles.append(one_tile)
        #print all_tiles
        return all_tiles
    
                
    def getExtents(self, tile):
            z = start_zoom + zoomFactor
           #print tile
            p0 = (tile[0] * 256, (tile[1] + 1) * 256)
            p1 = ((tile[0] + 1) * 256, tile[1] * 256)
            # Convert to LatLong (EPSG:4326)
            l0 = self.tileproj.fromPixelToLL(p0, z)
            l1 = self.tileproj.fromPixelToLL(p1, z)
            # Convert to map projection (e.g. mercator co-ords EPSG:900913)
            c0 = prj.forward(mapnik.Coord(l0[0],l0[1]))
            c1 = prj.forward(mapnik.Coord(l1[0],l1[1]))
        
            tile_extent = (c0.x,c0.y, c1.x,c1.y)
            return tile_extent, z

    

if __name__ == "__main__":
    dialog = TilesDialog()
    dialog.show()
    Gtk.main()
    
    
    
    
###*****************Unused or old versions of functions*****************###

def render_on_demand_for_a_speedTest(self, tile_uri, zoom, zentral_tile):
        logs = os.getenv("HOME") + '/TileGen/log-files/'
        wobj = open(logs+'TileGen-multi-vs-loop-rendering.txt', 'a')
        start_time = time.time()
        result, scale = new_object.render_on_demand_as_multiprocessing(tile_uri, zoom, zentral_tile)
        wobj.write('\n')
        wobj.write('\nMultiprocessing - took:'+str(round(time.time()-start_time, 3)) + ' seconds!')
        wobj.write('\n\t--> zentral tile:%s & zoomfactor: %s' %(str(zentral_tile), str(zoom)))
        wobj.write('\n***********************************************')
        start_time = time.time()
        result, scale = new_object.render_on_demand_as_loop(tile_uri, zoom, zentral_tile)
        wobj.write('\nLoop-processing - took:'+str(round(time.time()-start_time, 3)) + ' seconds!')
        wobj.write('\n\t--> zentral tile:%s & zoomfactor: %s' %(str(zentral_tile), str(zoom)))
        wobj.write('\n***********************************************')
        wobj.close()

def setButtonLabel(self, visible):        
        
        if len(self.buttonLabels) == 0:
            self.buttonLabels.append(self.ui.button_right.get_label())
            self.buttonLabels.append(self.ui.button_reload.get_label())
            self.buttonLabels.append(self.ui.button_zoom_out.get_label())
            self.buttonLabels.append(self.ui.button_left.get_label())
            self.buttonLabels.append(self.ui.button_up.get_label())
            self.buttonLabels.append(self.ui.button_down.get_label())
            self.buttonLabels.append(self.ui.button_zoom_in.get_label())
        if visible == True:
            self.ui.button_right.set_label(self.buttonLabels[0])
            self.ui.button_reload.set_label(self.buttonLabels[1])
            self.ui.button_zoom_out.set_label(self.buttonLabels[2])
            self.ui.button_left.set_label(self.buttonLabels[3])
            self.ui.button_up.set_label(self.buttonLabels[4])
            self.ui.button_down.set_label(self.buttonLabels[5])
            self.ui.button_zoom_in.set_label(self.buttonLabels[6])
        elif visible == False:
            self.ui.button_right.set_label('')
            self.ui.button_reload.set_label('')
            self.ui.button_zoom_out.set_label('')
            self.ui.button_left.set_label('')
            self.ui.button_up.set_label('')
            self.ui.button_down.set_label('')
            self.ui.button_zoom_in.set_label('')
#*****************************************
def render_on_demand_old_version(self, tile_uri, zoom, zentral_tile, buffer_size):
        rendered_tiles = []
        args = []
       #print zentral_tile
        for k in range(-1,2):
          for l in range(-1,2):
                start_time = time.time()
                if not os.path.isdir(tile_uri + '/' + str(zentral_tile[0]+k)):
                    os.mkdir(tile_uri + '/' + str(zentral_tile[0]+k))
                uri = tile_uri + '/' + str(zentral_tile[0]+k) + '/' + str(zentral_tile[1]+l) + '.png'
           #                #print uri
                                                    #Original call of tile rendering
                                                    #renderer.render_tile(uri, zentral_tile[0]+k, zentral_tile[1]+l, zoom, buffer_size)#(tile_uri, x, y, z)
                #store all the necessary informations of one tile in an array and collect all in an huge array
                #       --> this has to be done, as it is only possible to send ONE variable to the multiprocessing
                arg = (tile_dir, mapfile, maxZoom, uri, zentral_tile[0]+k, zentral_tile[1]+l, zoom, buffer_size)
                args.append(arg)
                                                    #Test of the newly created function 'pure_tile_rendering'
                                                    #rendering.pure_tile_rendering(arg)
                rendered_tiles.append(uri)    
                #print self.m.scale()/0.00028
                #self.wobj.write( uri+'\n')
                #self.wobj.write('took: '+str(time.time() - start_time)+ ' seconds\n')

        #Process tile rendering as multiprocessing using python intern modul
        pool = Pool(processes = 5)
        pool.map(rendering.pure_tile_rendering, args)

        
                                                    #second alternative of multiprocessing which uses an additional modul 'pprocess'
                                            #      nproc = 4      # maximum number of simultaneous processes desired
                                            #        results = pprocess.Map(limit=nproc, reuse=1)
                                            #        parallel_function = results.manage(pprocess.MakeReusable(rendering.pure_tile_rendering))    
                                            #        [parallel_function(args2) for args2 in args];  # Start computing things
                                            #        parallel_results = results[0:10]

        #returns not the actually rendered tiles but the uri of the tiles that should be rendered
        #print rendered_tiles
        return rendered_tiles
    