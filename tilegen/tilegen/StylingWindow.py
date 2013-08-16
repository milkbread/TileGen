from gi.repository import Gtk
import mapnik
import time
import os
from tilegen import xmlFunctions



class StylingWindow(Gtk.Window):
    
    def __init__(self, logfiles, main_window, name = "styling_window", file = "./data/ui/Toolbars.glade"):
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
        
        self.rule_chosen = False
        self.previewLayer_name = 'preview'
        self.style_problem = False
        
###Initializations 
    def initializeContents(self):
        self.comboboxtext_layer = self.builder.get_object('comboboxtext_layer')
        self.comboboxtext_layer.connect("changed", self.on_comboboxtext_layer_changed)
        self.comboboxtext_style = self.builder.get_object('comboboxtext_style')
        self.comboboxtext_style.connect("changed", self.on_comboboxtext_style_changed)
        self.comboboxtext_rules = self.builder.get_object('comboboxtext_rules')
        self.comboboxtext_rules.connect("changed", self.on_comboboxtext_rules_changed)
        self.label_status = self.builder.get_object('label_status')
        self.textview_symbols = self.builder.get_object('textview_symbols')
        self.switch_preview = self.builder.get_object('switch_preview')
        self.preview_box = self.builder.get_object('preview_box')
        self.showPreviewBox(False)
        self.switch_preview.set_active(False)
        self.switch_preview.connect("button-press-event", self.on_switch_preview_activate)
        self.entry_color = self.builder.get_object('entry_color')
        self.entry_color.set_text('rgb(100%,0%,100%)')
        self.checkbutton_scaledenom = self.builder.get_object('checkbutton_scaledenom')
        
        
    def initializeStylingWindow(self, mapnik_map, tiles_window, info_window, wps_window, initialAim):
        self.info_window = info_window
        self.wps_window = wps_window
        self.initialAim = initialAim
        self.commonInitializations(mapnik_map, tiles_window)
        
    def commonInitializations(self, mapnik_map, tiles_window):
        self.tiles_window = tiles_window
        self.mapnik_map = mapnik_map
        #initial information request of the used style-file to be able to choose a geometry for generalization
        #loop through all layers
        self.comboboxtext_layer.remove_all()
        for layer in self.mapnik_map.layers.__iter__():
            self.comboboxtext_layer.append_text(layer.name)         
        
    def showWindow(self):
        if self.closed == True:
            self.main_window.ui.mnu_styling.set_label(self.main_window.menuItemIndicator + self.main_window.ui.mnu_styling.get_label())
            self.window.show_all()
            self.closed = False
            
    def hideWindow(self):
        if self.closed == False:
            self.main_window.ui.mnu_styling.set_label(self.main_window.ui.mnu_styling.get_label().split(self.main_window.menuItemIndicator)[1])
            self.window.hide()
            self.closed = True
            
    def destroyWindow(self):
        self.window.destroy()
        if self.closed == False:
            self.main_window.ui.mnu_styling.set_label(self.main_window.ui.mnu_styling.get_label().split(self.main_window.menuItemIndicator)[1])

            
###Listeners
    def closedThisWindow(self, window, event):
        self.hideWindow()
        return True #this prevents the window from getting destroyed
        
    def on_switch_preview_activate(self, widget, event):
        if self.rule_chosen == True and self.tiles_window.getInitializationStatus() == True:
            #****this is a bugfix --> not able to connect signal 'acitvate'
            #solution = use button-press-event
            #disadvantage = .get_active() is changed after this function...and returns wrong value when applied here
            if self.switch_preview.get_active() == True:
                switch_preview_active = False
            elif self.switch_preview.get_active() == False:
                switch_preview_active = True
            #*****
            self.previewVisialisation(switch_preview_active)
        
    def on_comboboxtext_rules_changed(self, widget, data=None):
        rule_index = self.comboboxtext_rules.get_active()
        self.textview_symbols.get_buffer().set_text('') 
        
        if rule_index != -1:
            if self.comboboxtext_rules.get_active_text() != 'Style contains no rule!':
                self.textview_symbols.get_buffer().set_text('') 
                
                rule = self.mapnik_rules[rule_index]
                self.filter = rule[2]
                self.scaleDenoms = rule[4]
                for symbol in rule[3]:
                    symbol_type = symbol[0].type()
                    end_iter = self.textview_symbols.get_buffer().get_end_iter()                 #help: http://ubuntuforums.org/showthread.php?t=426671
                    self.textview_symbols.get_buffer().insert(end_iter,symbol_type + "Symbolizer") 
                    for key in symbol[1].keys():
                        self.textview_symbols.get_buffer().insert(end_iter,"\n"+ key +":" + symbol[1][key]) 
                    self.rule_chosen = True
                
                if self.initialAim == 1:# and self.info_window.getStatus() == False:
                    self.info_window.initializeInfoWindow(self.mapnik_map, self.tiles_window, self)
                    self.info_window.showWindow()
                elif self.initialAim == 2:# and self.wps_window.getStatus() == False:
                    self.wps_window.initializeWPSWindow(self.mapnik_map, self.tiles_window, self)
                    self.wps_window.showWindow()
                    
                #only show preview if user wants to
                if self.tiles_window.getInitializationStatus == True:
                    self.previewVisialisation(False)
    
                    if self.switch_preview.get_active() == True:
                        #set the preview of chosen geometries
                        self.previewVisialisation(self.switch_preview.get_active())
                    
            else:
                    self.label_status.set_text('No processing without any rule!!!')
        else:
            if self.style_problem == False:
                self.label_status.set_text('No rule chosen!')
            else:
                self.label_status.set_text("Style - '%s' - does not exist" %self.chosen_style_name)
                
        
    def on_comboboxtext_layer_changed(self, widget, data=None):
        self.comboboxtext_style.remove_all()
        chosen_layer = self.comboboxtext_layer.get_active_text()  
        self.mapnik_styles = [] 
        #find the chosen layer
        for layer in self.mapnik_map.layers.__iter__():
           if chosen_layer == layer.name:
               source_params = xmlFunctions.getDatasourceFromString(mapnik.save_map_to_string(self.mapnik_map),chosen_layer)
               type = source_params['type']
               #print type
               if type == 'shape' or type == 'postgis':
                   self.datasource = (source_params['type'], layer.datasource, source_params)
                   self.layerSRS = layer.srs
                   for style in layer.styles:
                       self.mapnik_styles.append(style)
                       self.comboboxtext_style.append_text(style)
               else:
                    print 'Please implement the missing type: %s' %type
                    self.comboboxtext_style.append_text('Layer type: %s ... it is not implemented yet!' %type)
    
    
    def on_comboboxtext_style_changed(self, widget, data=None):
        self.comboboxtext_rules.remove_all()
#        self.textview_symbols.get_buffer().set_text('') 
        if self.comboboxtext_style.get_active() != -1 :
            self.chosen_style_name = self.comboboxtext_style.get_active_text()
            #print self.chosen_style_name
            try:
                self.chosen_style = self.mapnik_map.find_style(self.chosen_style_name)
                self.mapnik_rules = []
                #loop through all rules of the chosen style
                if self.chosen_style.rules.__len__() == 0:
                    self.comboboxtext_rules.append_text('Style contains no rule!')
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
                        self.comboboxtext_rules.append_text(rule_content)
            
            except:
                self.style_problem = True
                        
            #print 'Number of rules: ', len(self.mapnik_rules)
            #print self.mapnik_rules[0]
            self.comboboxtext_rules.set_active(0)
    
    
###Functions

    def getStatus(self):
        return self.closed
        
    def previewVisialisation(self, actived):
          if actived == True:
            if self.checkbutton_scaledenom.get_active() == True:
                self.tiles_window.addPreviewToMap(self.previewLayer_name, self.scaleDenoms, self.filter, self.symbol_type, self.datasource, self.layerSRS, self.entry_color.get_text())
            else:
                self.tiles_window.addPreviewToMap(self.previewLayer_name, -1, self.filter, self.symbol_type, self.datasource, self.layerSRS, self.entry_color.get_text())
            self.tiles_window.reloadMapView()
          elif actived == False:
            self.mapnik_map.remove_style(self.previewLayer_name)
            self.tiles_window.reloadMapView()
            
    def showPreviewBox(self, visiblity):
        self.preview_box.set_child_visible(visiblity)
        