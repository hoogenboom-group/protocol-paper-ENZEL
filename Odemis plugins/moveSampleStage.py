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
import logging
from odemis import dataio, model
from odemis.acq import stream, acqmng
from odemis.acq.stream import StaticStream, FluoStream, SEMStream
import odemis.gui
from odemis.gui.conf import get_acqui_conf, util
from odemis.util import dataio as udataio
import time
import threading
import wx
from odemis.gui.plugin import Plugin, AcquisitionDialog
from odemis.gui.comp.text import UnitFloatCtrl
import cv2

class moveSampleStage(Plugin):
    name = "moveSampleStage"
    __version__ = "0.1"
    __author__ = "Daan Boltje"
    __license__ = "GPLv2"
    
    vaconf = OrderedDict((
        ("rx", {
            "label": "Rx",
            "accuracy": 18, # avoid dropping units from linked field
        }),
        ("rz", {
            "label": "Rz",
            "accuracy": 18, # avoid dropping units from linked field
        }),
        ("x", {
            "label": "x",
            "accuracy": 18, # avoid dropping units from linked field
        }),
        ("y", {
            "label": "y",
            "accuracy": 18, # avoid dropping units from linked field
        }),
        ("z", {
            "label": "z",
            "accuracy": 18, # avoid dropping units from linked field
        }),
        ("dz", {
            "label": "dz",
            "accuracy": 18, # avoid dropping units from linked field
        }),
    ))


    def __init__(self, microscope, main_app):
        super(moveSampleStage, self).__init__(microscope, main_app)

        self._dlg = None

        # Can only be used with a microscope
        if not microscope:
            return

        # Get components by role
        try:
            self.stage = model.getComponent(role="stage")
        except LookupError:
            logging.info("Hardware not found, cannot use the Move stage plugin.")
            return

        # TODO should check if microscope has a stage connection
        self.addMenu("Cryo/Move stage...", self._position_stage)
        
        self.shield_pos = {'x': -0.005468263998000001, 
                           'y': -0.00867527761136524, 
                           'z': 0.001056795793872422, 
                           'rx': -0.027931323924749046, 
                           'rz': 5.1140346198211525e-05}
                           
        self.rx = model.FloatContinuous(np.rad2deg(self.shield_pos['rx']), 
                                        [np.rad2deg(lim) for lim in self.stage.axes['rx'].range], 
                                         unit='deg')
        self.rz = model.FloatContinuous(np.rad2deg(self.shield_pos['rz']), 
                                        [np.rad2deg(lim) for lim in self.stage.axes['rz'].range], 
                                        unit='deg')
        self.x = model.FloatContinuous(self.shield_pos['x'], self.stage.axes['x'].range, unit='m')
        self.y = model.FloatContinuous(self.shield_pos['y'], self.stage.axes['y'].range, unit='m')
        self.z = model.FloatContinuous(self.shield_pos['z'], self.stage.axes['z'].range, unit='m')
        self.dz = model.FloatContinuous(50e-6, (10e-6, 200e-6), unit='m')
        
        self.move_order = ['x', 'y', 'rx', 'rz', 'z', ]

    def _position_stage(self):
        dlg = AcquisitionDialog(self, "Move sample stage", "Move order: x, y, z, Rx, Rz\nDefault position: chamber shield\nMove stage to position:")
        self._dlg = dlg
        
        dlg.addSettings(self, self.vaconf)
        
        dlg.addButton("Done")
        dlg.addButton("Move", self.move, face_colour='blue')
        dlg.addButton("Z+", self.zUp, face_colour='blue')
        dlg.addButton("Z-", self.zDown, face_colour='blue')

        ans = dlg.ShowModal()
        
        if ans == 0 or ans == wx.ID_CANCEL:
            logging.info("Move stage near shield done")
        elif ans == 1:
            logging.info("Move stage near shield completed")
        else:
            logging.warning("Got unknown return code %s", ans)

        dlg.Close()
        dlg.Destroy()
        self._dlg = None
        
    def move(self,dlg):
        thread = threading.Thread(target=self.position_stage, args=(dlg,))
        thread.start()

    def position_stage(self, dlg):
        for ax in self.move_order:
            pos = getattr(self, ax).value
            if 'r' in ax: 
                pos = np.deg2rad(pos)
            logging.info("Move stage axis %s to %f", ax, pos)
            self.stage.moveAbs({ax:pos}).result()
        
    def zUp(self, dlg):
        self.stage.moveRel({'z':self.dz.value}).result()

        
    def zDown(self, dlg):
        self.stage.moveRel({'z':-1.0*self.dz.value}).result() 
        
