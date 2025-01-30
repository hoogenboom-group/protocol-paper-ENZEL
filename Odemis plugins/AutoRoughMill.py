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


from __future__ import division
import os
import math
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from concurrent.futures._base import CancelledError, CANCELLED, FINISHED, RUNNING
from odemis.acq.feature import FEATURE_ACTIVE, FEATURE_ROUGH_MILLED, FEATURE_DEACTIVE, FEATURE_POLISHED
import logging
from odemis import dataio, model
from odemis.acq import stream, acqmng
from odemis.acq.stream import StaticStream, FluoStream, SEMStream
import odemis.gui
from odemis.gui.conf import get_acqui_conf, util
from odemis.gui import conf
from odemis.util import dataio as udataio
from odemis.gui.util import get_picture_folder
import time
import threading
import wx
from odemis.gui.plugin import Plugin, AcquisitionDialog
from odemis.gui.comp.text import UnitFloatCtrl
import cv2

class AutoRoughMill(Plugin):
    name = "AutoRoughMill"
    __version__ = "0.1"
    __author__ = "Daan Boltje"
    __license__ = "GPLv2"
    
    vaconf = OrderedDict((
        ("act", {
            "label": "Per feature action",
            "control_type": odemis.gui.CONTROL_RADIO,
            "choices": {0: u"Relief cuts", 1: u"Rough milling", 2: u"Relief cuts & rough milling", 3: u"2 um milling", 4: u"1 um milling"},
        }),
    ))
    
    def __init__(self, microscope, main_app):
        super(AutoRoughMill, self).__init__(microscope, main_app)

        self._dlg = None

        # Can only be used with a microscope
        if not microscope:
            return
        else:
            # Check which stream the microscope supports
            self.main_data = self.main_app.main_data
            if not (self.main_data.stage):
                return
                
        # Get components by role self.main_data = self.main_app.main_data
        try:
            self.stage = model.getComponent(role="stage")
            self.sem = model.getComponent("SEM XT Connection")
        except LookupError:
            logging.info("Hardware not found, cannot use the AutoRoughMilling stage plugin.")
            return

        self.def_sr = 180.0
        self.action = {0:0.012, 1:0.013, 2:0.011, 3:0.014, 4:0.015}
        self.label = {0:"Relief Cuts", 1:"Rough Milling", 2:"RC and RM", 3:"2 um", 4:"1 um"}
        self.act = model.VAEnumerated(0, choices={0, 1, 2, 3, 4})

        # TODO should check if microscope has a stage connection
        self.addMenu("Milling/Auto mill...", self.start)


    def start(self):
        # Fail if the live tab is not selected
        tab = self.main_app.main_data.tab.value
        if tab.name not in ("secom_live", "sparc_acqui", "cryosecom-localization"):
            available_tabs = self.main_app.main_data.tab.choices.values()
            exp_tab_name = "localization" if "cryosecom-localization" in available_tabs else "acquisition"
            box = wx.MessageDialog(self.main_app.main_frame,
                       "Automated rough milling must be started from the %s tab." % (exp_tab_name,),
                       "Automated rough milling not possible", wx.OK | wx.ICON_STOP)
            box.ShowModal()
            box.Destroy()
            return
        
        dlg = AcquisitionDialog(self, "Automated rough milling", "LM stream names most contain 'Acq' to automatically acquire images.\n ACTIVE Feature states are processed")
        self._dlg = dlg
        
#        dlg._dmodel.tool.choices = {
#            0,
#            1,
#            2,
#            3,
#            4,
#        }
#        
#        self.tool = dlg._dmodel.tool
        
        dlg.addSettings(self, self.vaconf)
        dlg.addButton("Cancel")
        dlg.addButton("Run action", self._auto_mill, face_colour='blue')
        dlg.addButton("Acq imgs", self.acq_imgs, face_colour='blue')


        ans = dlg.ShowModal()
        
        if ans == 0 or ans == wx.ID_CANCEL:
            logging.info("Automated milling cancelled")
        elif ans == 1:
            logging.info("Automated milling completed")
        elif ans == 2:
            logging.info("Automated image acquisition completed")
        else:
            logging.warning("Got unknown return code %s", ans)

        dlg.Close()
        dlg.Destroy()
        self._dlg = None
                

    def _set_rot(self, rot):
        self.sem.set_rotation(np.deg2rad(self.def_sr+rot))
        time.sleep(2.0)
        
    def _acq_and_save_images(self, streams, fe_name, status):
        config = conf.get_acqui_conf()
        exporter = dataio.get_converter(config.last_format)
        extension = config.last_extension
        dirname = get_picture_folder()
        basename = time.strftime("%Y%m%d-%H%M%S ", time.localtime())
        imgs = []
        for s in streams:
            if not "electrons" in s.name.value and ("Acq" in s.name.value or s.name.value == "RLM"):
                s.raw = []
                s.single_frame_acquisition.value = True
                s.should_update.value = True
                while not s.raw: time.sleep(1)
                filepath = os.path.join(dirname, basename + fe_name + " " + s.name.value + " " + status + extension)
                s.should_update.value = False
                imgs.append(s.raw[0])
                exporter.export(filepath, s.raw[0])
        filepath = os.path.join(dirname, basename + fe_name + " " + status + extension)
        exporter.export(filepath, imgs)
        for s in streams:
            if s.name.value == "RLM":
                s.single_frame_acquisition.value = False
                s.should_update.value = True

    def acq_imgs(self, dlg):
        main_data = self.main_app.main_data
        tab = self.main_app.main_data.tab.value
        tab_data = tab.tab_data_model
        action = self.action[self.act.value]
        try:
            f = model.ProgressiveFuture()
            f.task_canceller = lambda l: True  # To allow cancelling while it's running
            f.set_running_or_notify_cancel()  # Indicate the work is starting now
            dlg.showProgress(f)
            initt = time.time()
            fs = main_data.features.value
            features = [f for f in fs if not f.status.value == FEATURE_DEACTIVE]
            nb = len(features)
            done = 0
            for fe in features:
                currt = time.time()
                left = nb - done
                if done > 0: dur = left * (currt - initt) / done
                else: dur = nb * 5 * 60 #default estimate 5 min per site
                f.set_progress(end=currt + dur)
                if f.cancelled():
                    dlg.resumeSettings()
                    return
                pos = fe.pos.value
                logging.info(f"Moving to position: {pos}")
                self.main_data.stage.moveAbs({'x': pos[0], 'y': pos[1]})
                self.main_data.focus.moveAbs({'z': pos[2]})
                time.sleep(2.0)
                self._acq_and_save_images(tab_data.streams.value, fe.name.value, "ImgAcq")
                time.sleep(2.0)
                done += 1
            f.set_result(None)  # Indicate it's over
        finally:
            for s in tab_data.streams.value:
                if not "electrons" in s.name.value:
                    s.should_update.value = False
                    s.single_frame_acquisition.value = False
        logging.debug("Closing dialog")
        dlg.Close()

    def _auto_mill(self, dlg):
        """
        Automated rough milling operation.
        """
        main_data = self.main_app.main_data
        tab = self.main_app.main_data.tab.value
        tab_data = tab.tab_data_model
        action = self.action[self.act.value]
                
        try:
            f = model.ProgressiveFuture()
            f.task_canceller = lambda l: True  # To allow cancelling while it's running
            f.set_running_or_notify_cancel()  # Indicate the work is starting now
            dlg.showProgress(f)
            initt = time.time()
            fs = main_data.features.value
            features = [f for f in fs if f.status.value == FEATURE_ACTIVE]
            nb = len(features)
            done = 0
            sr = self.sem.get_rotation()
            for fe in features:
                currt = time.time()
                left = nb - done
                if done > 0: dur = left * (currt - initt) / done
                else: dur = nb * 5 * 60 #default estimate 5 min per site
                f.set_progress(end=currt + dur)
                if f.cancelled():
                    dlg.resumeSettings()
                    return
                pos = fe.pos.value
                logging.info(f"Moving to position: {pos}")
                self.main_data.stage.moveAbs({'x': pos[0], 'y': pos[1]})
                self.main_data.focus.moveAbs({'z': pos[2]})
                time.sleep(2.0)
                self._acq_and_save_images(tab_data.streams.value, fe.name.value, "PreMill")
                time.sleep(2.0)
                self._set_rot(action)
                while not np.abs(self.sem.get_rotation() - sr) < 0.0001:
                    if f.cancelled():
                        dlg.resumeSettings()
                        return
                    time.sleep(4)
                if self.act.value > 0: fe.status.value = FEATURE_ROUGH_MILLED
                self._acq_and_save_images(tab_data.streams.value, fe.name.value, self.label[self.act.value])
                done += 1
            f.set_result(None)  # Indicate it's over
        finally:
            for s in tab_data.streams.value:
                if not "electrons" in s.name.value:
                    s.should_update.value = False
                    s.single_frame_acquisition.value = False


        logging.debug("Closing dialog")
        dlg.Close()
