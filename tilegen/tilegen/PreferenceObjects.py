import os
import time
import pickle   #http://docs.python.org/2/library/pickle.html
from gi.repository import Gtk

class ProjectFile:
    def __init__(self):
        self.pure_extension = 'tgn'
        self.blank_title = 'untitled'
        self.projectFilename = self.blank_title
    
    def setProjectFile(self, filename):
        extension = '.'+self.pure_extension
        cache = filename.split('.')
        if len(cache) == 1:
            self.projectFilename = filename + extension
        elif len(cache) == 2:
            if cache[1] == self.pure_extension:
                self.projectFilename = filename
            else:
                self.projectFilename = cache[0] + extension
        else:
            print "You've got a problem for the file extension on that file: %s"%filename
    
    def getProjectFile(self):
        return self.projectFilename
        
    def getPureFileName(self):
        if self.isBlank():
            return self.projectFilename
        parts = self.projectFilename.split("/")
        for part in parts:
            if part.find(self.pure_extension) != -1:
                return part
        return self.projectFilename
        
    #saving this object as binary file
    def saveAsBinary(self, main_params):
        if self.projectFilename != '':
            output = open(self.projectFilename, 'wb')            
            # Pickle this class using the highest protocol available.
            pickle.dump(main_params, output, -1)
            output.close()
            return True
        else:
            return False
            
    def loadProject(self):
        tgn_file = open(self.getProjectFile(), 'rb')
        loaded_project = pickle.load(tgn_file)
        tgn_file.close()
        return loaded_project
            
    def saveProjectWindow(self, main_window, params):
        dialog = Gtk.FileChooserDialog("Please choose a file", main_window, 
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_name('%s.%s'%(self.blank_title, self.pure_extension))
        return self.finishWindowProcessing(dialog, params)
        
    def openProjectWindow(self, main_window, params):
        dialog = Gtk.FileChooserDialog("Please choose a file", main_window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        return self.finishWindowProcessing(dialog, params)
    
    def finishWindowProcessing(self, dialog, params):
        dialog.set_filename(params.getGeneralHome()+'projectfiles/*')
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            output = (dialog.get_filename(), True)
        elif response == Gtk.ResponseType.CANCEL:
            output = (self.blank_title, False)
        dialog.destroy()
        self.setProjectFile(output[0])
        return output[1]
        
    def isBlank(self):
        return self.projectFilename == self.blank_title

class FilesNLogs:
    global working_folder
    global log_files_folder_name
    global log_file_name
    global tiles_folder_name
    global image_name
    global xml_files_folder_name
    
    working_folder = '/TileGen/'
    log_files_folder_name = 'log-files/'
    log_file_name = 'TileGen-log.txt'
    tiles_folder_name = 'tiles/'
    image_name = "user_image.png"
    xml_files_folder_name = 'xmlfiles/'
    
    def __init__(self):
        self.home = os.getenv("HOME")
        self.generalHome = self.home + working_folder
        self.logs = self.generalHome + log_files_folder_name
        self.logfile_name = self.logs+log_file_name
        self.tile_dir = self.generalHome + tiles_folder_name 
        self.previewImage = self.generalHome + image_name
        self.xml_files_folder = self.generalHome + xml_files_folder_name
        
        self.checkFolderExistence(self.generalHome)
        self.checkFolderExistence(self.logs)
        self.checkFolderExistence(self.tile_dir)
        self.checkFolderExistence(self.xml_files_folder)
        
        self.initializeUserInputs()
        #initialize a logfile
        self.logfile = Logfile(self.logfile_name)
        
        self.minZoom = '0'
        self.maxZoom = '18'
        self.buffer = '128'
        
    def initializeUserInputs(self):
        self.user_path = ''
        self.chosen_mapfile_name = ''
        self.mapfileHome = ''
        self.projectFilename = ''
        self.extentSourceDefined = False
            
    def getHome(self):
        return self.home
    def getGeneralHome(self):
        return self.generalHome
    def getLogfilesHome(self):
        return self.logs
    def getTilesHome(self):
        return self.tile_dir
    def getPreviewImage(self):
        return self.previewImage
    def getXMLFilesHome(self):
        return self.xml_files_folder
        
    def checkFolderExistence(self, folder):
        if not os.path.isdir(folder):
            os.mkdir(folder)
    
    def writeToLog(self, content):
        self.logfile.writeToLog(content)
    
    #user defined inputs
    def setUserPath(self, path):
        self.user_path = path + '/'        
    def setMapfile(self, mapfile):
        self.chosen_mapfile_name = mapfile
        self.mapfileHome = self.user_path + mapfile
    def setZoomRange(self, minZoom, maxZoom):
        self.minZoom = minZoom
        self.maxZoom = maxZoom 
    def setBuffer(self, buffer):
        self.buffer = buffer
    def setExtentSource(self, type, name):
        self.extentSourceType = type
        self.extentSourceName = name
        self.extentSourceDefined = True

    #user input dependend outputs
    def getUserPath(self):
        return self.user_path
    def getMapfile(self):
        return self.chosen_mapfile_name
    def getMapfileHome(self):
        return self.mapfileHome
    def getZoomRange(self):
        return self.minZoom, self.maxZoom
    def getBuffer(self):
        return self.buffer
    def getExtentSource(self):
        if self.extentSourceDefined == True:
            return self.extentSourceType, self.extentSourceName
        else:
            return False
    def getExtentStatus(self):
        return self.extentSourceDefined
    
class Definitions:
    def __init__(self):
        self.menuItemIndicator = "<  "
        self.textEditor = 'gedit'      
        self.minimal_mapnik_version = 200100
        self.mapnik_version_warning = "You're having a too old version of mapnik...install minimum version 2.1.0!!!"
        self.initial_project_title = 'untitled'
        
    def getIndicator(self):
        return self.menuItemIndicator
    def getEditor(self):
        return self.textEditor
    def getMinMapnikVersion(self):
        return self.minimal_mapnik_version, self.mapnik_version_warning
    def getInitialTitle(self):
        return self.initial_project_title
    
        
class Logfile:
    def __init__(self, logs):
        self.logs = logs
        self.file = open(logs,"a")
        self.file.write('\n***********************************************************')
        self.file.write('\n'+str(time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())))
        self.file.close()
    def writeToLog(self, content):
        self.file = open(self.logs,"a")
        self.file.write("\n"+content)
        self.file.close()
    def closeLogfile(self):
        self.file.close()
        