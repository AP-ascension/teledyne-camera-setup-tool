# Camera Setup Tool
- This repository houses a camera setup tool designed to facilitate camera configuration and image capture. THis is a repo branched from a project started by @JagButtar for setup of HT cameras. This repo is simply a camera interface swap with the original program to allow use of Teledyne cameras, specifically the FLIR BlackFly Model.

# Overview:
- Design:

	Contains GUI design files that are editable using Gluonix Designer. This allows customization of the graphical interface according to your needs.
- Runtime:

	Includes the runtime files necessary for running the tool. The runtime requires Python 3.10, but the design module can be exported to run with other Python versions as well.

# Features
- Camera Settings Adjustment:
- Exposure
- Gamma
- Gain
- Contrast -> Not implemented as FLIR does not offer contrast adjustment
- Saturation
- Sharpness
- Image Size (not yet implemented)
- Image Capture:

	Supports capturing multiple images using a recording feature.

	Allows capturing a single image with a grab button.

- Customizable Image Save Path:

	Users can specify the path where captured images are saved.

# Installation
```
git clone https://github.com/AP-ascension/teledyne-camera-setup-tool.git
cd teledyne-camera-Setup-Tool
cd Runtime
Ensure you have the spinnaker sdk python wheel in the Runtime folder
pip install -r requirements.txt
```

# Requirements
- Gluonix Designer Runtime Requirements
- Spinnaker Wheel Install
- PySpin Python Library

# Running
- First do cd Runtime
- Lastly, run python Camera.py

# Limitations
- If you start two separate camera setup tools and select the same camera for both of them, you will have shared memory conflict. I dont plan on fixing this as I dont know why one would ever want to do this.
