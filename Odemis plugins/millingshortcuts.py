# -*- coding: utf-8 -*-
"""
Created on Jun 19 2023

@author: Daan Boltje

Plugin that controls milling by setting minor changes to scan rotation
(requires "LamellaMillingCommands.xrml" running in iFast).

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
from odemis.gui.conf import get_acqui_conf
from odemis.util import dataio as udataio
import time
import threading
import wx
from odemis.gui.plugin import Plugin, AcquisitionDialog
import cv2


class MillingShortcuts(Plugin):
    name = "MillingShortcuts"
    __version__ = "0.1"
    __author__ = "Daan Boltje"
    __license__ = "GPLv2"

    def __init__(self, microscope, main_app):
        super(MillingShortcuts, self).__init__(microscope, main_app)

        self._dlg = None

        # Can only be used with a microscope
        if not microscope:
            return

        # Get components by role
        try:
            self.sem = model.getComponent("SEM XT Connection")
        except LookupError:
            logging.info("Hardware not found, cannot use the Milling plugin.")
            return

        # TODO should check if microscope has an XT connection
        self.addMenu("Milling/Stop\tCtrl+`", self._stop_milling)
        self.addMenu("Milling/Stress relieve cuts\tCtrl+1", self._mill_p1)
        self.addMenu("Milling/2.5 um\tCtrl+2", self._mill_p2)
        self.addMenu("Milling/1.0 um\tCtrl+3", self._mill_p3)
        self.addMenu("Milling/0.6 um\tCtrl+4", self._mill_p4)
        self.addMenu("Milling/0.2 um\tCtrl+5", self._mill_p5)
        self.addMenu("Milling/3-beam alignment hole\tCtrl+6", self._mill_p6)
        self.addMenu("Milling/Mill RC & RM", self._run_rc_rm)



        # Initialize parameters
        self.def_sr = 180.0

    def _stop_milling(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr-0.001))

    def _mill_p1(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.001))

    def _mill_p2(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.002))

    def _mill_p3(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.003))

    def _mill_p4(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.004))

    def _mill_p5(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.005))

    def _mill_p6(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.006))
        
    def _mill_beam_align(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.007))
        
    def _run_rc_rm(self):
        self.sem.set_rotation(np.deg2rad(self.def_sr+0.011))

