from . import L_CameraSDK as SDK
import cv2
import numpy as np
import time

def Search():
    return SDK.CameraEnumerateDevice()

class Camera:
    def __init__(self):
        self._Config = ['ID', 'Exposure', 'Gain', 'Gamma', 'Contrast', 'Sharpness', 'Saturation', 'Width', 'Height', 'Left', 'Top', 'Format']
        self._ID = False
        self._ID_Old = False
        self._Exposure = 25000
        self._Gain = 8
        self._Gamma = 100
        self._Contrast = 100
        self._Sharpness = 0
        self._Saturation = 0
        self._Width = 0
        self._Height = 0
        self._Left = 0
        self._Top = 0
        self._Format = 'MONO8'
        self._Filter = False
        
        self._DeviceInfo = False
        
    def __str__(self):
        return f"Camera[ID:{self._ID}]"
        
    def __repr__(self):
        return f"Camera[ID:{self._ID}]"
                
    @staticmethod
    def Search():
        Devices = []
        Device_List =  SDK.CameraEnumerateDevice()
        for Device in Device_List:
            Device = str(Device)
            Lines = Device.splitlines()
            Dict = {}
            for Line in Lines:
                Key, Value = Line.split(':', 1)
                Key, Value = Key.strip(), Value.strip()
                if Key=='acFriendlyName':
                    Dict['Name'] = Value
                if Key=='acSensorType':
                    Dict['Sensor'] = Value
                if Key=='acPortType':
                    Dict['Port'] = Value
                if Key=='acSn':
                    Dict['ID'] = Value
            Devices.append(Dict)
        return Devices
        
    @staticmethod    
    def Format():
        return ['MONO8', 'RGB8']
            
    def Info(self):
        Dict = {}
        if self._DeviceInfo:
            Device = str(self._DeviceInfo)
            Lines = Device.splitlines()
            for Line in Lines:
                Key, Value = Line.split(':', 1)
                Key, Value = Key.strip(), Value.strip()
                if Key=='acFriendlyName':
                    Dict['Name'] = Value
                if Key=='acSensorType':
                    Dict['Sensor'] = Value
                if Key=='acPortType':
                    Dict['Port'] = Value
                if Key=='acSn':
                    Dict['ID'] = Value
        return Dict
            
    def Size(self):
        if self._DeviceInfo:
            return {'Width': self.Cap.sResolutionRange.iWidthMax, 'Height': self.Cap.sResolutionRange.iHeightMax}
        else:
            return False
        
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
        if not self._DeviceInfo or (self._ID and (self._ID!=self._ID_Old)):
            Return = self.Connect()
            if Return:
                self._ID_Old = self._ID
                self.Create()
        if self._DeviceInfo:
            self.Update()
        
    def Connect(self):
        self.DeviceList = SDK.CameraEnumerateDevice()
        for Device in self.DeviceList:
            if self._ID in str(Device):
                self._DeviceInfo = Device
                self.CameraHandleX = SDK.c_int()
                SDK._sdk.CameraInit(SDK.byref(self._DeviceInfo), -1, -1, SDK.byref(self.CameraHandleX))
                self.CameraHandle = self.CameraHandleX.value
                self.Cap = SDK.CameraGetCapability(self.CameraHandle)
                return True
        return False
            
    def Correction(self, Fx, Fy, Cx, Cy, K1, K2, K3, P1, P2):
        if self._DeviceInfo:
            CameraMatrix = [Fx, Fy, Cx, Cy]
            DistortionParameter = [K1, K2, P1, P2, K3]
            SDK.CameraSetUndistortEnable(self.CameraHandle, True)
            SDK.CameraSetUndistortParams(self.CameraHandle, self._Width, self._Height, CameraMatrix, DistortionParameter)
        
    def Create(self):
        Trigger_Mode = []
        SDK.CameraSetIspOutFormat(self.CameraHandle, getattr(SDK, f'CAMERA_MEDIA_TYPE_{self._Format}'))
        if self._Width<1 or self._Width>(self.Cap.sResolutionRange.iWidthMax-self._Left):
            self._Width = self.Cap.sResolutionRange.iWidthMax-self._Left
        if self._Height<1 or self._Height>(self.Cap.sResolutionRange.iHeightMax-self._Top):
            self._Height = self.Cap.sResolutionRange.iHeightMax-self._Top
        SDK.CameraSetImageResolutionEx(self.CameraHandle, 255, 0, 0, self._Left, self._Top, self._Width, self._Height, 0, 0)
        SDK.CameraSetTriggerMode(self.CameraHandle, 1)
        SDK.CameraSetExtTrigSignalType(self.CameraHandle, 0)
        SDK.CameraSetStrobeMode(self.CameraHandle, 0)
        SDK.CameraSetAeState(self.CameraHandle, 0)
        SDK.CameraSetTriggerCount(self.CameraHandle, 1)
        SDK.CameraPlay(self.CameraHandle)
        self.FrameBufferSize = self.Cap.sResolutionRange.iWidthMax * self.Cap.sResolutionRange.iHeightMax
        self.FrameBuffer = SDK.CameraAlignMalloc(self.FrameBufferSize, 16)
        
    def Update(self):
        try:
            SDK.CameraSetExposureTime(self.CameraHandle, self._Exposure)
            SDK.CameraSetAnalogGain(self.CameraHandle, self._Gain)
            SDK.CameraSetSharpness(self.CameraHandle, self._Sharpness)
            SDK.CameraSetGamma(self.CameraHandle, self._Gamma)
            SDK.CameraSetContrast(self.CameraHandle, self._Contrast)
            SDK.CameraSetSaturation(self.CameraHandle, self._Saturation)
            SDK.CameraSetNoiseFilter(self.CameraHandle, self._Filter)
        except:
            return False
        
    def Set_Size(self):
        try:
            if self._Width<1 and self._Width>(self.Cap.sResolutionRange.iWidthMax-self._Left):
                self._Width = self.Cap.sResolutionRange.iWidthMax-self._Left
            if self._Height<1 and self._Height>(self.Cap.sResolutionRange.iHeightMax-self._Top):
                self._Height = self.Cap.sResolutionRange.iHeightMax-self._Top
            SDK.CameraPause(self.CameraHandle)
            SDK.CameraSetImageResolutionEx(self.CameraHandle, 255, 0, 0, self._Left, self._Top, self._Width, self._Height, 0, 0)
            SDK.CameraPlay(self.CameraHandle)
        except:
            return False
        
    def Trigger(self):
        if self._DeviceInfo:
            try:
                SDK.CameraSoftTrigger(self.CameraHandle)
                Raw_Data, Frame_Head = SDK.CameraGetImageBuffer(self.CameraHandle, 1000)
                SDK.CameraImageProcess(self.CameraHandle, Raw_Data, self.FrameBuffer, Frame_Head)
                SDK.CameraReleaseImageBuffer(self.CameraHandle, Raw_Data)
                SDK.CameraFlipFrameBuffer(self.FrameBuffer, Frame_Head, 1)
                Frame_Data = (SDK.c_ubyte * Frame_Head.uBytes).from_address(self.FrameBuffer)
                Frame = np.frombuffer(Frame_Data, dtype=np.uint8)
                if self._Format == 'MONO8':
                    Frame = Frame.reshape((Frame_Head.iHeight, Frame_Head.iWidth, 1))
                    Frame = cv2.cvtColor(Frame, cv2.COLOR_GRAY2RGB)
                else:
                    Frame = Frame.reshape((Frame_Head.iHeight, Frame_Head.iWidth, 3))
                return Frame
            except:
                return False
        else:
            return False
    
    def Close(self):
        if self._DeviceInfo:
            try:
                SDK.CameraUnInit(self.CameraHandle)
                SDK.CameraAlignFree(self.FrameBuffer)
            except:
                return False