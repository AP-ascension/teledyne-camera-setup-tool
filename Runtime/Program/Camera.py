# -------------------------------------------------------------------------------------------------------------------------------
# Gluonix Runtime
# -------------------------------------------------------------------------------------------------------------------------------
#################################################################################################################################
from Nucleon.Runner import * ###!REQUIRED ------- Any Script Before This Won't Effect GUI Elements
#################################################################################################################################
#################################################################################################################################
# -------------------------------------------------------------------------------------------------------------------------------
# Developer Programming Start
# -------------------------------------------------------------------------------------------------------------------------------

from Connect import Camera

import time
import _thread
import os
import cv2
import PIL
from pathlib import Path
from datetime import datetime

Camera_List = []
Current_Camera = False
Camera_Run = False
Camera_Pause = False
Camera_Paused = False
Record_Run = False
Grab_Run = False
Record_Increment = 0
Save_Type = 'Images'
Save_Path = str(Path.home() / "Downloads")

#Camera Connect
Root.Connect.Search.Bind(On_Click = lambda E: Search())
Root.Connect.Search.Config(Border_Color='#adadad', Background='#e1e1e1')
Root.Connect.Search.Bind(On_Hover_In=lambda E: Root.Connect.Search.Config(Border_Color='#0078d7', Background='#d5dcf0'))
Root.Connect.Search.Bind(On_Hover_Out=lambda E: Root.Connect.Search.Config(Border_Color='#adadad', Background='#e1e1e1'))

Root.Connect.Connect.Bind(On_Click = lambda E: Connect())
Root.Connect.Connect.Config(Border_Color='#adadad', Background='#e1e1e1')
Root.Connect.Connect.Bind(On_Hover_In=lambda E: Root.Connect.Connect.Config(Border_Color='#0078d7', Background='#d5dcf0'))
Root.Connect.Connect.Bind(On_Hover_Out=lambda E: Root.Connect.Connect.Config(Border_Color='#adadad', Background='#e1e1e1'))

def Connect():
    global Current_Camera, Camera_Run
    Device = Root.Connect.List.Get()
    if Device:
        Device = Device.split('-')
        SN = Device[len(Device)-1]
        Current_Camera = Camera()
        Current_Camera.Config(ID=SN)
        Camera_Run = True
        _thread.start_new_thread(Run_Camera, ())
        Root.Connect.Hide()
        Root.Search.Hide()
        Root.Control.Show()
        Update()

def Run_Camera():
    global Camera_Run, Current_Camera, Camera_Pause, Camera_Paused, Record_Run, Grab_Run, Save_Type, Record_Increment
    while True:
        if not Camera_Run:
            Current_Camera.Close()
            Current_Camera = False
            break
        if Camera_Pause:
            Camera_Paused = True
            time.sleep(0.01)
        else:
            Camera_Paused = False
            Frame = Current_Camera.Trigger()
            if Frame is not False:
                if Record_Run or Grab_Run:
                    Name_Time = time.time()
                    Milliseconds = int(round(Name_Time * 1000))
                    Name_Date = datetime.fromtimestamp(Name_Time)
                    Milliseconds_Part = Milliseconds % 1000
                    Name_Date_Formatted = Name_Date.strftime('%Y%m%d-%H%M%S') + f'.{Milliseconds_Part:03d}'
                    if Save_Type=='Images':
                        cv2.imwrite(f"{Save_Path}/Image-{Name_Date_Formatted}.bmp", Frame)
                        if Grab_Run:
                            Grab_Run = False
                        else:
                            Record_Increment += 1
                            Root.Control.Record.Set(f"RECORDING ({Record_Increment})")
                Root.After(1, lambda : Load_Frame(Frame))
        
def Load_Frame(Frame):
    Temp_Frame = Frame.copy()
    Root.Control.Display.Set(Temp_Frame)
        
def Update():
    if Current_Camera:
        Setting = Current_Camera.Config_Get('Exposure', 'Gain', 'Gamma', 'Contrast', 'Sharpness', 'Saturation', 'Width', 'Height', 'Left', 'Top')
        Info = Current_Camera.Info()
        Size = Current_Camera.Size()
        Root.Control.Name.Entry.Set(Info['Name'])
        Root.Control.ID.Entry.Set(Info['ID'])
        Root.Control.Image_Size.Entry.Set(f"{Size['Width']} X {Size['Height']}")
        Root.Control.Exposure.Entry.Set(Setting['Exposure'])
        Root.Control.Exposure.Scale.Set(Setting['Exposure'])
        Root.Control.Gain.Entry.Set(Setting['Gain'])
        Root.Control.Gain.Scale.Set(Setting['Gain'])
        Root.Control.Gamma.Entry.Set(Setting['Gamma'])
        Root.Control.Gamma.Scale.Set(Setting['Gamma'])
        Root.Control.Contrast.Entry.Set(Setting['Contrast'])
        Root.Control.Contrast.Scale.Set(Setting['Contrast'])
        Root.Control.Sharpness.Entry.Set(Setting['Sharpness'])
        Root.Control.Sharpness.Scale.Set(Setting['Sharpness'])
        Root.Control.Saturation.Entry.Set(Setting['Saturation'])
        Root.Control.Saturation.Scale.Set(Setting['Saturation'])
        Root.Control.Width_Height.Width_Entry.Set(Setting['Width'])
        Root.Control.Width_Height.Height_Entry.Set(Setting['Height'])
        Root.Control.Left_Top.Left_Entry.Set(Setting['Left'])
        Root.Control.Left_Top.Top_Entry.Set(Setting['Top'])

# Camera Search
def Search():
    Root.Connect.Hide()
    Root.Control.Hide()
    Root.Search.Show()
    _thread.start_new_thread(Search_Progress, ())
    
def Search_Init():
    global Camera_List
    Camera_List = Camera.Search()
    Root.Connect.List.Clear()
    for Device in Camera_List:
        Root.Connect.List.Add(f"{Device['Name']}-{Device['Sensor']}-{Device['Port']}-{Device['ID']}")
        
def Search_Progress():
    for X in range(0, 1001):
        Root.Search.Bar.Set(X/10)
        time.sleep(0.001)
        if X==700:
            _thread.start_new_thread(Search_Init, ())
    Root.Search.Hide()
    Root.Control.Hide()
    Root.Connect.Show()
    
#Control
Root.Control.Display.Config(Array=True)

Root.Control.Switch.Bind(On_Click = lambda E: Switch())
Root.Control.Switch.Config(Border_Color='#adadad', Background='#AED6F1')
Root.Control.Switch.Bind(On_Hover_In=lambda E: Root.Control.Switch.Config(Border_Color='#0078d7', Background='#5DADE2'))
Root.Control.Switch.Bind(On_Hover_Out=lambda E: Root.Control.Switch.Config(Border_Color='#adadad', Background='#AED6F1'))

Root.Control.Exposure.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Exposure', 'Entry'))
Root.Control.Exposure.Scale.Bind(On_Change = lambda E: Update_Camera('Exposure', 'Scale'))
Root.Control.Exposure.Scale.Config(Minimum=100, Maximum=1000000, Increment=1)

Root.Control.Gain.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Gain', 'Entry'))
Root.Control.Gain.Scale.Bind(On_Change = lambda E: Update_Camera('Gain', 'Scale'))
Root.Control.Gain.Scale.Config(Minimum=8, Maximum=176, Increment=1)

Root.Control.Gamma.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Gamma', 'Entry'))
Root.Control.Gamma.Scale.Bind(On_Change = lambda E: Update_Camera('Gamma', 'Scale'))
Root.Control.Gamma.Scale.Config(Minimum=0, Maximum=200, Increment=1)

Root.Control.Contrast.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Contrast', 'Entry'))
Root.Control.Contrast.Scale.Bind(On_Change = lambda E: Update_Camera('Contrast', 'Scale'))
Root.Control.Contrast.Scale.Config(Minimum=0, Maximum=200, Increment=1)

Root.Control.Sharpness.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Sharpness', 'Entry'))
Root.Control.Sharpness.Scale.Bind(On_Change = lambda E: Update_Camera('Sharpness', 'Scale'))
Root.Control.Sharpness.Scale.Config(Minimum=0, Maximum=100, Increment=1)

Root.Control.Saturation.Entry.Bind(On_Key_Release = lambda E: Update_Camera('Saturation', 'Entry'))
Root.Control.Saturation.Scale.Bind(On_Change = lambda E: Update_Camera('Saturation', 'Scale'))
Root.Control.Saturation.Scale.Config(Minimum=0, Maximum=100, Increment=1)

Root.Control.Set_Size.Bind(On_Click = lambda E: Start_Set_Size())
Root.Control.Set_Size.Config(Border_Color='#adadad', Background='#AED6F1')
Root.Control.Set_Size.Bind(On_Hover_In=lambda E: Root.Control.Set_Size.Config(Border_Color='#0078d7', Background='#5DADE2'))
Root.Control.Set_Size.Bind(On_Hover_Out=lambda E: Root.Control.Set_Size.Config(Border_Color='#adadad', Background='#AED6F1'))

Root.Control.Width_Height.Width_Entry.Bind(On_Key_Release = lambda E: Update_Size('Width_Height', 'Width'))

Root.Control.Width_Height.Height_Entry.Bind(On_Key_Release = lambda E: Update_Size('Width_Height', 'Height'))

Root.Control.Left_Top.Left_Entry.Bind(On_Key_Release = lambda E: Update_Size('Left_Top', 'Left'))

Root.Control.Left_Top.Top_Entry.Bind(On_Key_Release = lambda E: Update_Size('Left_Top', 'Top'))

Root.Control.Save_Path.Entry.Set(Save_Path)
Root.Control.Save_Path.Entry.Config(Align='left')
Root.Control.Save_Path.Entry.Bind(On_Key_Release=lambda E: Check_Save_Path())

Root.Control.Save_Path.Browse.Bind(On_Click = lambda E: Get_Save_Path())
Root.Control.Save_Path.Browse.Config(Border_Color='#adadad', Background='#F2F3F4')
Root.Control.Save_Path.Browse.Bind(On_Hover_In=lambda E: Root.Control.Save_Path.Browse.Config(Border_Color='#0078d7', Background='#B3B6B7'))
Root.Control.Save_Path.Browse.Bind(On_Hover_Out=lambda E: Root.Control.Save_Path.Browse.Config(Border_Color='#adadad', Background='#F2F3F4'))

Root.Control.Recorder.Type.Add('Videos')
Root.Control.Recorder.Type.Add('Images')
Root.Control.Recorder.Type.Set('Images')
Root.Control.Recorder.Hide()
Root.Control.Separator4.Hide()

Root.Control.Record.Bind(On_Click = lambda E: Recorder())
Root.Control.Record.Config(Border_Color='#239B56', Background='#ABEBC6')

Root.Control.GrabX.Bind(On_Click = lambda E: Grabber())
Root.Control.GrabX.Config(Border_Color='#2874A6', Background='#AED6F1')

Root.Maximize()

def Switch():
    global Camera_Run, Record_Run
    Record_Run = False
    Camera_Run = False
    Root.Control.Record.Config(Value='START RECORDING', Border_Color='#239B56', Background='#ABEBC6')
    Search()
    
def Update_Camera(Type, Widget):
    Setting = getattr(Root.Control, Type)
    Entry = getattr(Setting, 'Entry')
    Scale = getattr(Setting, 'Scale')
    if Entry.Get() and Scale.Get():
        if Widget=='Entry':
            Value = int(Entry.Get())
            Scale.Set(Value)
        else:
            Value = int(Scale.Get())
            Entry.Set(Value)
        if Current_Camera:
            Current_Camera.Config(**{Type: Value})
            
def Update_Size(Type, Sub):
    Setting = getattr(Root.Control, Type)
    Entry = getattr(Setting, f'{Sub}_Entry')
    if Entry.Get():
        Value = int(Entry.Get())
        if Current_Camera:
            Current_Camera.Config(**{Sub: Value})
            
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
        Root.Control.Save_Path.Entry.Set(Save_Path)
        Root.Control.Save_Path.Entry.Config(Bordor_Color='black')

def Check_Save_Path():
    global Save_Path
    Temp_Path = Root.Control.Save_Path.Entry.Get()
    if os.path.exists(Temp_Path):
        Save_Path = Temp_Path
        Root.Control.Save_Path.Entry.Config(Border_Color='black')
    else:
        Root.Control.Save_Path.Entry.Config(Border_Color='red')
        
def Recorder():
    global Record_Run, Save_Type, Record_Increment
    if Record_Run:
        Record_Run = False
        Root.Control.Record.Config(Value='START RECORDING', Border_Color='#239B56', Background='#ABEBC6')
    else:
        Save_Type = Root.Control.Recorder.Type.Get()
        Root.Control.Record.Config(Value='RECORDING (0)', Border_Color='#B03A2E', Background='#F5B7B1')
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