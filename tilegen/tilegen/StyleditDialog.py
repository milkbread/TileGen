# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk # pylint: disable=E0611

from tilegen_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('tilegen')

from tilegen import functions as func


class StyleditDialog(Gtk.Dialog):
    __gtype_name__ = "StyleditDialog"

    def __new__(cls, sent):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated StyleditDialog object.
        """
        global stylefile
        stylefile = sent

        builder = get_builder('StyleditDialog')
        new_object = builder.get_object('styledit_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a StyleditDialog object with it in order to
        finish initializing the start of the new StyleditDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)

    #def on_button_map_clicked(self, widget, data=None):
        styles, layer, map_definition = func.getContents(stylefile)
        #print 'styles ' +str(map_definition)

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        pass

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        pass


if __name__ == "__main__":
    dialog = StyleditDialog()
    dialog.show()
    Gtk.main()
