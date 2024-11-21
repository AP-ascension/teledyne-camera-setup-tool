# Camera Setup Tool
- This repository houses a camera setup tool designed to facilitate camera configuration and image capture. THis is a repo branched from a project started by @JagButtar for setup of HT cameras. This repo is simply a camera interface swap with the original program to allow use of Teledyne cameras, specifically the FLIR BlackFly Model.

# Overview:
- Design:

	Contains GUI design files that are editable using Gluonix Designer. This allows customization of the graphical interface according to your needs.
- Runtime:

	Includes the runtime files necessary for running the tool. The runtime requires Python 3.11, but the design module can be exported to run with other Python versions as well.

# Features
- Camera Settings Adjustment:
- Exposure
- Gamma
- Gain
- Contrast
- Saturation (not yet implemented)
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
```

# Requirements
- Gluonix Designer Runtime Requirements
- Spinnaker Wheel Install
- PySpin Python Library
