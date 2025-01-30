# -*- coding: utf-8 -*-
"""
Created on Jun 19 2023

@author: Daan Boltje

Plugin to position sample stage near (just below) the cryogenic chamber shield.

This is free and unencumbered software released into the public domain.
Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.
The software is provided "as is", without warranty of any kind,
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose and non-infringement.
In no event shall the authors be liable for any claim, damages or
other liability, whether in an action of contract, tort or otherwise,
arising from, out of or in connection with the software or the use or
other dealings in the software.
"""

import os
import wx
from odemis import model
from odemis.gui.util import get_home_folder
from odemis.acq.feature import FEATURE_ACTIVE, FEATURE_ROUGH_MILLED, FEATURE_DEACTIVE, FEATURE_POLISHED, read_features
from odemis.gui.plugin import Plugin, AcquisitionDialog
import logging

class LoadFeatures(Plugin):
    name = "LoadFeatures"
    __version__ = "0.1"
    __author__ = "Daan Boltje"
    __license__ = "GPLv2"
    
    
    def __init__(self, microscope, main_app):
        super(LoadFeatures, self).__init__(microscope, main_app)

        self._dlg = None

        # Can only be used with a microscope
        if not microscope:
            return
        else: 
            self.main_data = self.main_app.main_data
                
        self.addMenu("Cryo/Load features...", self.load_features)
        self.addMenu("Cryo/Remove all features...", self.remove_all_features)
        
    def remove_all_features(self):
        # Fail if the live tab is not selected
        tab = self.main_app.main_data.tab.value
        if tab.name not in ("secom_live", "sparc_acqui", "cryosecom-localization"):
            available_tabs = self.main_app.main_data.tab.choices.values()
            exp_tab_name = "localization" if "cryosecom-localization" in available_tabs else "acquisition"
            box = wx.MessageDialog(self.main_app.main_frame,
                       "Removing features must be done from the %s tab." % (exp_tab_name,),
                       "Removing features not possible", wx.OK | wx.ICON_STOP)
            box.ShowModal()
            box.Destroy()
            return
        
        main_data = self.main_app.main_data
        main_data.features.value = []

    def load_features(self):
        # Fail if the live tab is not selected
        tab = self.main_app.main_data.tab.value
        if tab.name not in ("secom_live", "sparc_acqui", "cryosecom-localization"):
            available_tabs = self.main_app.main_data.tab.choices.values()
            exp_tab_name = "localization" if "cryosecom-localization" in available_tabs else "acquisition"
            box = wx.MessageDialog(self.main_app.main_frame,
                       "Loading features must be done from the %s tab." % (exp_tab_name,),
                       "Loading features not possible", wx.OK | wx.ICON_STOP)
            box.ShowModal()
            box.Destroy()
            return
        
        main_data = self.main_app.main_data
        fs = main_data.features.value
        
        dialog = wx.FileDialog(self.main_app.main_frame,
                               message="Choose a file to load",
                               defaultDir=get_home_folder(),
                               defaultFile="",
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                               wildcard="Features JSON (*.json)|*.json")

        # Show the dialog and check whether is was accepted or cancelled
        if dialog.ShowModal() != wx.ID_OK:
            return 

        filename = dialog.GetPath()
        logging.debug("Loading features file %s", filename)
        dirname = os.path.dirname(os.path.realpath(filename))
        fs = read_features(dirname)
        main_data.features.value = fs

