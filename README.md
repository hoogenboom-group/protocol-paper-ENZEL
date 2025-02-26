# protocol-paper-ENZEL

This repository contains all scripts used in the workflow described in the bio-protocol paper 'Workflow of a Coincident Fluorescence, Electron, and Ion Beam Microscope':
- Odemis plugins
- Fluorescence intensity monitor IFM-Monitor
- iFast script LamellaMillingCommands
In addition, it contains the STEP files describing the design of the custom glovebox-transfer module interface.

## Odemis plugins
These plugins are used in combination with Odemis version 3.3.0-174-g9355cac (https://github.com/delmic/odemis).
After installation of Odemis, they can be added to the plugins folder inside the odemis folder.

## IFM-Monitor
This jupyter notebook is used to monitor fluorescence intensity during lamella milling.
After installation of jupyter notebook, run ```jupyter notebook``` in the terminal, navigate to IFM-Monitor.ipynb, open it, and run the script.

## LamellaMillingCommands
This iFast script is used with iFast Developer’s Kit (version 5.1.10.2037).
Start up iFast Developer's Kit, open LamellaMillingCommands.xrml, and run.

## STEP files
This folder contains the 3D STEP files describing the design of the custom glovebox-transfer module interface.
This includes both STEP files of the separate components as well as their combination.
