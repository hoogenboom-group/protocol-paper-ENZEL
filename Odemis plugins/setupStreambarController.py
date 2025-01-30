# -*- coding: utf-8 -*-
"""
Created on Jun 19 2023

@author: Daan Boltje

Plugin to set-up Streambar Controller

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


from __future__ import division
import os
import math
import numpy as np
import matplotlib.pyplot as plt
import odemis.acq.stream as acqstream

from collections import OrderedDict
from concurrent.futures._base import CancelledError, CANCELLED, FINISHED, RUNNING
import logging
from odemis import dataio, model
from odemis.acq import stream, acqmng
from odemis.acq.stream import StaticStream, FluoStream, SEMStream
import odemis.gui
from odemis.gui.conf import get_acqui_conf
from odemis.util import dataio as udataio
from odemis.util import conversion, fluo
import time
import threading
import wx
from odemis.gui.plugin import Plugin, AcquisitionDialog
from odemis.gui.comp.text import UnitFloatCtrl
import cv2


class SetStreambarController(Plugin):
    name = "SetStreambarController"
    __version__ = "0.1"
    __author__ = "Daan Boltje"
    __license__ = "GPLv2"
    

    def __init__(self, microscope, main_app):
        super(SetStreambarController, self).__init__(microscope, main_app)

        self._dlg = None

        # Can only be used with a microscope
        if not microscope:
            return
        else:
            # Check which stream the microscope supports
            self.main_data = self.main_app.main_data
            if not (self.main_data.ccd and self.main_data.light):
                return

        self.addMenu("Cryo/Set-up streams", self.setup)


    def add_stream(self, tab, name, power, excitation, emitter, exposuretime, tint, binning):
        tab_data = tab.tab_data_model
        _main_data_model = tab_data.main
        s = acqstream.FluoStream(
            name,
            _main_data_model.ccd,
            _main_data_model.ccd.data,
            _main_data_model.light,
            _main_data_model.light_filter,
            focuser=_main_data_model.focus,
            opm=_main_data_model.opm,
            detvas={"exposureTime", "binning"},
        )
        s.power.value = power
        s.excitation.value = excitation
        s.emission.value = emitter
        s.det_vas["exposureTime"].value = exposuretime
        s.det_vas["binning"].value = binning
        s.tint.value = tint
        sc = tab.streambar_controller._add_stream(s, add_to_view=True, play=False)
        sc.stream_panel.collapse(True)

    def setup(self):
        # Fail if the live tab is not selected
        tab = self.main_app.main_data.tab.value
        if tab.name not in ("secom_live", "sparc_acqui", "cryosecom-localization"):
            available_tabs = self.main_app.main_data.tab.choices.values()
            exp_tab_name = "localization" if "cryosecom-localization" in available_tabs else "acquisition"
            box = wx.MessageDialog(self.main_app.main_frame,
                       "Streams must be set up from the %s tab." % (exp_tab_name,),
                       "Setting up streams not possible", wx.OK | wx.ICON_STOP)
            box.ShowModal()
            box.Destroy()
            return
            
        # Stop the streams
        tab_data = tab.tab_data_model
        _main_data_model = tab_data.main
        add_streams = False
        for s in tab_data.streams.value:
            if isinstance(s, acqstream.FluoStream):
                ex_choices = s._emitter.spectra.value
                em_choices = s._em_filter.axes["band"].choices.copy()
                # convert any list into tuple, as lists cannot be put in a set
                for k, v in em_choices.items():
                    em_choices[k] = conversion.ensure_tuple(v)
                em_choices = [v for v in em_choices.values()]
                #tab.streambar_controller.removeStreamPanel(s)
                add_streams = True
        if add_streams:
            self.add_stream(tab, "RLMAcq", 10e-3, ex_choices[1], em_choices[0], 0.15, (255, 255, 255), (1,1))
            #self.add_stream(tab, "Pol", 15e-3, ex_choices[1], em_choices[1], 0.15, (255, 255, 255), (1,1))
            self.add_stream(tab, "Ex390Em440", 10e-3, ex_choices[0], em_choices[1], 0.5, (0, 0, 255), (2,2))
            self.add_stream(tab, "Ex485Em525", 10e-3, ex_choices[1], em_choices[2], 0.5, (55, 255, 0), (2,2))
            self.add_stream(tab, "Ex560Em607", 10e-3, ex_choices[2], em_choices[3], 0.5, (255, 149, 0), (2,2))
            self.add_stream(tab, "Ex648Em684", 10e-3, ex_choices[3], em_choices[4], 0.5, (255, 0, 0), (2,2))
            self.add_stream(tab, "Ex390Em440Acq", 10e-3, ex_choices[0], em_choices[1], 20.0, (0, 0, 255), (1,1))
            self.add_stream(tab, "Ex485Em525Acq", 10e-3, ex_choices[1], em_choices[2], 20.0, (55, 255, 0), (1,1))
            self.add_stream(tab, "Ex560Em607Acq", 10e-3, ex_choices[2], em_choices[3], 20.0, (255, 149, 0), (1,1))
            self.add_stream(tab, "Ex648Em684Acq", 10e-3, ex_choices[3], em_choices[4], 20.0, (255, 0, 0), (1,1))
        else:
            box = wx.MessageDialog(self.main_app.main_frame,
               "At least one optical stream needs to be present",
               "Setting up streams not possible", wx.OK | wx.ICON_STOP)
            box.ShowModal()
            box.Destroy()
