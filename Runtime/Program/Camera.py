# -------------------------------------------------------------------------------------------------------------------------------
# Gluonix Runtime
# -------------------------------------------------------------------------------------------------------------------------------
#################################################################################################################################
import PIL.Image
from Nucleon.Runner import * ###!REQUIRED ------- Any Script Before This Won't Effect GUI Elements
#################################################################################################################################
#################################################################################################################################

#################################################################################################################################
# Import Files
#################################################################################################################################
from FLIRModule import FLIRModule as CameraModule
from RPC import Client
from multiprocessing import shared_memory

import time
import _thread
import os, sys
import cv2
import PIL
from pathlib import Path
from datetime import datetime
import numpy as np


import socket, subprocess, sys, atexit

#################################################################################################################################
# Starting RPC Server
#################################################################################################################################

subprocesses = []

def cleanup():
    # Terminate all subprocesses when the main program exits
    for proc in subprocesses:
        proc.terminate()

# Register cleanup function to be called on program exit
atexit.register(cleanup)

def check_server(host, port):
    try:
        # Create a socket object
        with socket.create_connection((host, port), timeout=5):
            print(f"Server is running on {host}:{port}")
            return True
    except (socket.timeout, socket.error):
        print(f"No server found on {host}:{port}")
        return False

for no in range(0, 10):
    if not check_server('127.0.0.1', (61010 + no)):
        process = subprocess.Popen([sys.executable, "Program/FLIRServer.py"] + [str(no)])
        subprocesses.append(process)
        break
    else:
        print(f'Exisitng process running on port: {61010 + no}')

#################################################################################################################################
# Global Variables
#################################################################################################################################

rpc_client = Client(61010)
rpc_server_lock = _thread.allocate_lock()
shm = None

Camera_List = []
Current_Camera = False
Camera_Run = False
Camera_Pause = False
Camera_Paused = False
Record_Run = False
Grab_Run = False
Record_Increment = 0
Image_Loading = False
Save_Path = str(Path.home() / "Downloads")

#################################################################################################################################
# Global Classes
#################################################################################################################################

class Slider():

    def __init__(self, Bar, Frame):
        self._Config = ['On_Change', 'Minimum', 'Maximum', 'Increment']
        self._Bar = Bar
        self._Frame = Frame
        self._On_Change = False
        self._Minimum = 0
        self._Maximum = 100
        self._Increment = 1
        self._Bar.Set(0)
        self._Frame.Bind(On_Click=lambda E: self.Progress_Start(E), On_Drag=lambda E: self.Progress(E), On_Release=lambda E: self.On_Change())
        Bar_Data = self._Bar.Config_Get('Left', 'Width')
        Minimum = Bar_Data['Left']
        self._Frame.Config(Left=Minimum)
        self._Frame.Show()

    def On_Change(self):
        if self._On_Change:
            self._On_Change()

    def Config_Get(self, *Input):
        Return = {}
        for Each in self._Config:
            if Each in Input:
                Return[Each] = getattr(self, "_"+Each)
        return Return

    def Config(self, **Input):
        for Each in self._Config:
            if Each in Input:
                Value = Input[Each]
                setattr(self, "_"+Each, Value)

    def Get(self):
        Progress = self._Bar.Get()
        Range  = self._Maximum - self._Minimum
        Value = self._Minimum + (Progress / 100.0) * Range
        Value = round(Value / self._Increment) * self._Increment
        return Value

    def Set(self, Value):
        Range  = self._Maximum - self._Minimum
        Value = (Value - self._Minimum) / Range
        Value = Value * 100.0
        self._Bar.Set(Value)
        Bar_Data = self._Bar.Config_Get('Left', 'Width')
        Frame_Data = self._Frame.Config_Get('Left', 'Width')
        Minimum = Bar_Data['Left']
        Maximum = Bar_Data['Left']+Bar_Data['Width']-Frame_Data['Width']
        Frame_Left = Bar_Data['Left']+((Maximum-Minimum)*(Value/100))
        self._Frame.Config(Left=Frame_Left)

    def Progress_Start(self, E):
        self._Start = E.x

    def Progress(self, E):
        Frame_Data = self._Frame.Config_Get('Left', 'Width')
        Frame_Left = Frame_Data['Left'] + E.x - self._Start
        Bar_Data = self._Bar.Config_Get('Left', 'Width')
        Minimum = Bar_Data['Left']
        Maximum = Bar_Data['Left']+Bar_Data['Width']-Frame_Data['Width']
        Frame_Left = max(Minimum, min(Frame_Left, Maximum))
        Bar_Progress = (Frame_Left-Bar_Data['Left'])/(Maximum-Minimum)*100
        self._Bar.Set(Bar_Progress)
        self._Frame.Config(Left=Frame_Left)

#################################################################################################################################
# Programming
#################################################################################################################################

#Camera Connect
Root.Connect.Search.Bind(On_Click = lambda E: Search())
Root.Connect.Search.Config(Border_Color='#adadad', Background='#e1e1e1')
Root.Connect.Search.Bind(On_Hover_In=lambda E: Root.Connect.Search.Config(Border_Color='#0078d7', Background='#d5dcf0'))
Root.Connect.Search.Bind(On_Hover_Out=lambda E: Root.Connect.Search.Config(Border_Color='#adadad', Background='#e1e1e1'))

Root.Connect.Connect.Bind(On_Click = lambda E: Connect())
Root.Connect.Connect.Config(Border_Color='#adadad', Background='#e1e1e1')
Root.Connect.Connect.Bind(On_Hover_In=lambda E: Root.Connect.Connect.Config(Border_Color='#0078d7', Background='#d5dcf0'))
Root.Connect.Connect.Bind(On_Hover_Out=lambda E: Root.Connect.Connect.Config(Border_Color='#adadad', Background='#e1e1e1'))

Root.Connect.Format.Add("MONO")
Root.Connect.Format.Add("RGB")
Root.Connect.Format.Set("MONO")

camera_serial_number = None

def Connect():
    global Current_Camera, Camera_Run, rpc_client, camera_serial_number
    Device = Root.Connect.List.Get()
    Format = Root.Connect.Format.Get()+"8"
    print(f'Device Selected: {Device}')
    if Device:
        Device = Device.split('-')
        camera_serial_number = Device[-1]
        print(f'Connecting to camera with SN: {camera_serial_number}')
        # configure camera by serial number
        rpc_client.config(camera_serial_number)
        # here is where I will likely also have to initalize format
        Camera_Run = True
        Update()
        _thread.start_new_thread(Run_Camera, ())

        Root.Connect.Hide()
        Root.Search.Hide()
        Root.Control.Show()

def Run_Camera():
    global Camera_Run, Current_Camera, Camera_Pause, Camera_Paused, Record_Run, Grab_Run, Record_Increment, Image_Loading, rpc_client, shm, rpc_server_lock
    Image_Loading = False
    while True:
        if not Camera_Run:
            Current_Camera = False
            break
        if Camera_Pause:
            Camera_Paused = True
            Image_Loading = False
            time.sleep(0.01)
        else:
            Camera_Paused = False
            rpc_server_lock.acquire()
            dim = rpc_client.trigger()
            rpc_server_lock.release()
            if dim is not False:
                if Record_Run or Grab_Run:
                    Name_Time = time.time()
                    Milliseconds = int(round(Name_Time * 1000))
                    Name_Date = datetime.fromtimestamp(Name_Time)
                    Milliseconds_Part = Milliseconds % 1000
                    Name_Date_Formatted = Name_Date.strftime('%Y%m%d-%H%M%S') + f'.{Milliseconds_Part:03d}'
                    #Frame_CV = cv2.cvtColor(Frame, cv2.COLOR_RGB2BGR)
                    #cv2.imwrite(f"{Save_Path}/Image-{Name_Date_Formatted}.bmp", Frame_CV)
                    if Grab_Run:
                        Grab_Run = False
                    else:
                        Record_Increment += 1
                        Root.Control.Option.Record.Set(f"RECORDING ({Record_Increment})")
                if not Image_Loading:

                    Image_Loading = True
                    if shm is None:
                        shm = shared_memory.SharedMemory(name=f'cam{camera_serial_number}')
                    Temp_Frame = np.ndarray(dim, dtype=np.uint8, buffer=shm.buf)

                    if Temp_Frame.shape[2] == 1:
                        Temp_Frame = Temp_Frame.squeeze(axis=-1)  # Convert to 2D (height, width)
                        Temp_Frame = PIL.Image.fromarray(Temp_Frame)  # Create Pillow image (grayscale)

                    # If it's a color image (3 channels), ensure the shape is correct
                    elif Temp_Frame.shape[2] == 3:
                        Temp_Frame = PIL.Image.fromarray(Temp_Frame)  # Create Pillow image (RGB)

                    Root.After(0, lambda: Load_Frame(Temp_Frame))

def Load_Frame(Frame):
    global Image_Loading
    Root.Control.LiveView.Set(Frame)
    Image_Loading = False

def Update():
    global rpc_client, Camera_Run
    if Camera_Run:
        Setting = rpc_client.get_config()
        Info = rpc_client.get_info()
        Size = rpc_client.get_size()
        Root.Control.Info.Name.Entry.Set(Info[0])
        Root.Control.Info.ID.Entry.Set(Info[1])
        Root.Control.Info.Size.Entry.Set(f"{Size[0]} X {Size[1]}")
        Root.Control.Setup.Exposure.Entry.Set(Setting[0])
        Root.Control.Setup.Exposure.Scale.Set(Setting[0])
        Root.Control.Setup.Gain.Entry.Set(Setting[1])
        Root.Control.Setup.Gain.Scale.Set(Setting[1])
        Root.Control.Setup.Gamma.Entry.Set(Setting[2])
        Root.Control.Setup.Gamma.Scale.Set(Setting[2])
        Root.Control.Setup.Contrast.Entry.Set(Setting[3])
        Root.Control.Setup.Contrast.Scale.Set(Setting[3])
        Root.Control.Setup.Sharpness.Entry.Set(Setting[4])
        Root.Control.Setup.Sharpness.Scale.Set(Setting[4])
        Root.Control.Setup.Saturation.Entry.Set(Setting[5])
        Root.Control.Setup.Saturation.Scale.Set(Setting[5])
        Root.Control.Size.Width.Entry.Set(Setting[6])
        Root.Control.Size.Height.Entry.Set(Setting[7])
        Root.Control.Size.Left.Entry.Set(Setting[8])
        Root.Control.Size.Topx.Entry.Set(Setting[9])

# Camera Search
def Search():
    Root.Connect.Hide()
    Root.Control.Hide()
    Root.Search.Show()
    _thread.start_new_thread(Search_Progress, ())

def Search_Init():
    global Camera_List
    Camera_List = CameraModule.Search()
    Root.Connect.List.Clear()
    for Device in Camera_List:
        Root.Connect.List.Add(f"{Device['DeviceDisplayName']}-{Device['DeviceSerialNumber']}")

def Search_Progress():
    for X in range(0, 101):
        Root.Search.Bar.Set(X)
        time.sleep(0.001)
        if X==1:
            _thread.start_new_thread(Search_Init, ())
    Root.Search.Hide()
    Root.Control.Hide()
    Root.Connect.Show()

#Control
Root.Control.LiveView.Config(Pil=True)

Root.Control.Option.Switch.Bind(On_Click = lambda E: Switch())
Root.Control.Option.Switch.Config(Border_Color='#adadad', Background='#AED6F1')
Root.Control.Option.Switch.Bind(On_Hover_In=lambda E: Root.Control.Option.Switch.Config(Border_Color='#0078d7', Background='#5DADE2'))
Root.Control.Option.Switch.Bind(On_Hover_Out=lambda E: Root.Control.Option.Switch.Config(Border_Color='#adadad', Background='#AED6F1'))

Root.Control.Setup.Exposure.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Exposure', 'Entry'))
Root.Control.Setup.Exposure.Scale = Slider(Root.Control.Setup.Exposure.Bar, Root.Control.Setup.Exposure.Frame)
Root.Control.Setup.Exposure.Scale.Config(On_Change = lambda : Update_Camera('Exposure', 'Scale'))
Root.Control.Setup.Exposure.Scale.Config(Minimum=100, Maximum=1000000, Increment=1)

Root.Control.Setup.Gain.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Gain', 'Entry'))
Root.Control.Setup.Gain.Scale = Slider(Root.Control.Setup.Gain.Bar, Root.Control.Setup.Gain.Frame)
Root.Control.Setup.Gain.Scale.Config(On_Change = lambda : Update_Camera('Gain', 'Scale'))
Root.Control.Setup.Gain.Scale.Config(Minimum=8, Maximum=176, Increment=1)

Root.Control.Setup.Gamma.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Gamma', 'Entry'))
Root.Control.Setup.Gamma.Scale = Slider(Root.Control.Setup.Gamma.Bar, Root.Control.Setup.Gamma.Frame)
Root.Control.Setup.Gamma.Scale.Config(On_Change = lambda : Update_Camera('Gamma', 'Scale'))
Root.Control.Setup.Gamma.Scale.Config(Minimum=0, Maximum=200, Increment=1)

Root.Control.Setup.Contrast.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Contrast', 'Entry'))
Root.Control.Setup.Contrast.Scale = Slider(Root.Control.Setup.Contrast.Bar, Root.Control.Setup.Contrast.Frame)
Root.Control.Setup.Contrast.Scale.Config(On_Change = lambda : Update_Camera('Contrast', 'Scale'))
Root.Control.Setup.Contrast.Scale.Config(Minimum=0, Maximum=200, Increment=1)

Root.Control.Setup.Sharpness.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Sharpness', 'Entry'))
Root.Control.Setup.Sharpness.Scale = Slider(Root.Control.Setup.Sharpness.Bar, Root.Control.Setup.Sharpness.Frame)
Root.Control.Setup.Sharpness.Scale.Config(On_Change = lambda : Update_Camera('Sharpness', 'Scale'))
Root.Control.Setup.Sharpness.Scale.Config(Minimum=0, Maximum=100, Increment=1)

Root.Control.Setup.Saturation.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Saturation', 'Entry'))
Root.Control.Setup.Saturation.Scale = Slider(Root.Control.Setup.Saturation.Bar, Root.Control.Setup.Saturation.Frame)
Root.Control.Setup.Saturation.Scale.Config(On_Change = lambda : Update_Camera('Saturation', 'Scale'))
Root.Control.Setup.Saturation.Scale.Config(Minimum=0, Maximum=100, Increment=1)

Root.Control.Size.Set.Bind(On_Click = lambda E: Start_Set_Size())
Root.Control.Size.Set.Config(Border_Color='#adadad', Background='#AED6F1')
Root.Control.Size.Set.Bind(On_Hover_In=lambda E: Root.Control.Size.Set.Config(Border_Color='#0078d7', Background='#5DADE2'))
Root.Control.Size.Set.Bind(On_Hover_Out=lambda E: Root.Control.Size.Set.Config(Border_Color='#adadad', Background='#AED6F1'))

Root.Control.Size.Width.Entry.Bind(On_Key_Release = lambda E: Update_Size('Width', 'Width'))

Root.Control.Size.Height.Entry.Bind(On_Key_Release = lambda E: Update_Size('Height', 'Height'))

Root.Control.Size.Left.Entry.Bind(On_Key_Release = lambda E: Update_Size('Left', 'Left'))

Root.Control.Size.Topx.Entry.Bind(On_Key_Release = lambda E: Update_Size('Topx', 'Top'))

Root.Control.Path.Entry.Set(Save_Path)
Root.Control.Path.Entry.Config(Align='left')
Root.Control.Path.Entry.Bind(On_Key_Release=lambda E: Check_Save_Path())

Root.Control.Path.Browse.Bind(On_Click = lambda E: Get_Save_Path())
Root.Control.Path.Browse.Config(Border_Color='#adadad', Background='#F2F3F4')
Root.Control.Path.Browse.Bind(On_Hover_In=lambda E: Root.Control.Path.Browse.Config(Border_Color='#0078d7', Background='#B3B6B7'))
Root.Control.Path.Browse.Bind(On_Hover_Out=lambda E: Root.Control.Path.Browse.Config(Border_Color='#adadad', Background='#F2F3F4'))

Root.Control.Option.Record.Bind(On_Click = lambda E: Recorder())
Root.Control.Option.Record.Config(Border_Color='#239B56', Background='#ABEBC6')

Root.Control.Option.GrabX.Bind(On_Click = lambda E: Grabber())
Root.Control.Option.GrabX.Config(Border_Color='#2874A6', Background='#AED6F1')

def Switch():
    global Camera_Run, Record_Run
    Record_Run = False
    Camera_Run = False
    Root.Control.Option.Record.Config(Value='START RECORDING', Border_Color='#239B56', Background='#ABEBC6')
    Search()

def Update_Camera(Type, Widget):
    global rpc_client, rpc_server_lock
    try:
        Setting = getattr(Root.Control.Setup, Type)
        Entry = getattr(Setting, 'Entry')
        Scale = getattr(Setting, 'Scale')
        if Entry.Get():
            if Widget=='Entry':
                Value = int(Entry.Get())
                Scale.Set(Value)
            else:
                Value = int(Scale.Get())
                Entry.Set(Value)

            rpc_server_lock.acquire()
            if Type=='Exposure':
                print(f'Value of exposure to be set: {Value}')
                rpc_client.set_exposure(Value)
            elif Type=='Gain':
                rpc_client.set_gain(Value)
            elif Type=='Gamma':
                rpc_client.set_gamma(Value)
            elif Type=='Contrast':
                rpc_client.set_contrast(Value)
            elif Type=='Sharpness':
                rpc_client.set_sharpness(Value)
            elif Type=='Saturation':
                rpc_client.set_saturation(Value)
            rpc_server_lock.release()

    except:
        print("Error updating camera.")


def Update_Size(Type, Sub):
    global rpc_client, rpc_server_lock

    try:
        Entry = getattr(Root.Control.Size, Type).Entry
        if Entry.Get():
            Value = int(Entry.Get())

            rpc_server_lock.acquire()
            if Type=='Width':
                rpc_client.set_width(Value)
            elif Type=='Height':
                rpc_client.set_height(Value)
            elif Type=='Topx':
                rpc_client.set_top(Value)
            elif Type=='Left':
                rpc_client.set_left(Value)
            rpc_server_lock.release()
    except:
        print("Error updating camera.")

def Start_Set_Size():
    _thread.start_new_thread(Set_Size, ())

def Set_Size():
    global Camera_Pause, Camera_Paused
    if Current_Camera:
        while not Camera_Paused:
            Camera_Pause = True
            time.sleep(0.01)
        Current_Camera.Set_Size()
        Camera_Pause = False

def Get_Save_Path():
    global Save_Path
    Initial=''
    if Save_Path:
        Initial = Save_Path
    Temp_Path = Root.Folder(Initial=Initial, Title='Select Output Directory')
    if Temp_Path!='':
        Save_Path = Temp_Path
        Root.Control.Path.Entry.Set(Save_Path)
        Root.Control.Path.Entry.Config(Bordor_Color='black')

def Check_Save_Path():
    global Save_Path
    Temp_Path = Root.Control.Path.Entry.Get()
    if os.path.exists(Temp_Path):
        Save_Path = Temp_Path
        Root.Control.Path.Entry.Config(Border_Color='black')
    else:
        Root.Control.Path.Entry.Config(Border_Color='red')

def Recorder():
    global Record_Run, Record_Increment
    if Record_Run:
        Record_Run = False
        Root.Control.Option.Record.Config(Value='START RECORDING', Border_Color='#239B56', Background='#ABEBC6')
    else:
        Root.Control.Option.Record.Config(Value='RECORDING (0)', Border_Color='#B03A2E', Background='#F5B7B1')
        Record_Increment = 0
        Record_Run = True

def Grabber():
    global Grab_Run
    Grab_Run = True

def Close_Camera():
    global Camera_Run, Current_Camera
    Camera_Run = False
    if Current_Camera:
        Current_Camera.Close()
        Current_Camera = False

Root.Bind(On_Close=lambda : Close_Camera())


#Start
Search()

# -------------------------------------------------------------------------------------------------------------------------------
# Developer Programming End
# -------------------------------------------------------------------------------------------------------------------------------
#################################################################################################################################
#################################################################################################################################
Root.Start() ###!REQUIRED ------- Any Script After This Will Not Execute
#################################################################################################################################