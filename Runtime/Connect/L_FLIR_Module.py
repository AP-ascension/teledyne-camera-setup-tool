import PySpin as SDK
import numpy as np
import _thread
from multiprocessing import shared_memory
import time

camera_SN_database = {
    1: '24310060',
    2: '24310057'
}

class FLIR_Module:
    def __init__(self):
        self._Config = ['ID', 'exposure', 'gain', 'gamma', 'Contrast', 'sharpness', 'saturation', 'Width', 'Height', 'Left', 'Top', 'Format']
        self._ID = False
        self._ID_Old = False
        self._exposure = 25000
        self._gain = 8
        self._gamma = 100
        self._Contrast = 100
        self._sharpness = 0
        self._saturation = 0
        self._Width = 0
        self._Height = 0
        self._Left = 0
        self._Top = 0
        self._Format = 'MONO8'
        self._Filter = False

        self.system = None
        self.device_list = None
        self.device = None
        self.node_map = None
        self.run_camera = True

        self.sm = None
        self.trigger_command = None

    def __str__(self):
        return f"Camera[ID:{self._ID}]"

    def __repr__(self):
        return f"Camera[ID:{self._ID}]"

    @staticmethod
    def Search():
        Devices = []
        Key_List = ['DeviceDisplayName', 'DeviceSerialNumber']
        System = SDK.System.GetInstance()
        Device_List = System.GetCameras()
        for Device in Device_List:
            TL_Device = Device.GetTLDeviceNodeMap()
            Device_Info = SDK.CCategoryPtr(TL_Device.GetNode("DeviceInformation"))
            if SDK.IsReadable(Device_Info):
                Features = Device_Info.GetFeatures()
                Dict = {}
                for Feature in Features:
                    Temp_Feature = SDK.CValuePtr(Feature)
                    if SDK.IsReadable(Temp_Feature):
                        Key = Temp_Feature.GetName()
                        Value = Temp_Feature.ToString()
                        if Key in Key_List:
                            Dict[Key] = Value
                Devices.append(Dict)
        Device_List.Clear()
        System.ReleaseInstance()
        return Devices
    @staticmethod
    def Format():
        return ['MONO8', 'RGB8']

    def Size(self):
        if self.Device_Info:
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
        print('FLIR_Module: Config()')
        # change attributes of specified parameters
        for Each in self._Config:
            if Each in Input:
                Value = Input[Each]
                setattr(self, "_"+Each, Value)

        # If no device connected or the ID has changed, connect to camera specified by ID number
        if self.device is None and (self._ID and (self._ID!=self._ID_Old)):
            device_found = self.Connect()

            if device_found:
                self._ID_Old = self._ID
                self.configure_trigger()
            else:
                print("No camera connected! Exiting")
                return False

        self.Update()

    def Connect(self):
        print('FLIR_Module: Connect()')
        if self.system is None:
            self.system = SDK.System.GetInstance()
        self.device_list = self.system.GetCameras()

        num_cameras = self.device_list.GetSize()

        print('Number of cameras detected: %d' % num_cameras)

        # Finish if there are no cameras
        if num_cameras == 0:
            # Clear camera list before releasing system
            self.device_list.Clear()

            # Release system instance
            self.system.ReleaseInstance()

            print('Not enough cameras!')
            input('Done! Press Enter to exit...')
            return False

        for idx, device in enumerate(self.device_list):
            print(f'Device: {idx}')

            device_serial_number = SDK.CStringPtr(device.GetTLDeviceNodeMap().GetNode("DeviceSerialNumber"))

            if SDK.IsReadable(device_serial_number):
                device_serial_number = device_serial_number.GetValue()

                # Cameras are initalized with IDs. They use this ID to reference a database
                # where the camera serial number can be found. I am using a dictionary to mimic
                # the database in the meantime.
                if camera_SN_database.get(self._ID)==device_serial_number:
                    self.device = device

                    self.device.Init()
                    self.node_map = self.device.GetNodeMap()

                    return True

        return False

    def configure_trigger(self):
        print('FLIR_Module: configure_trigger()')
        try:
            #--------------------------------------------------------------------------------
            # turn trigger mode off - trigger mode must be off to configure trigger
            #--------------------------------------------------------------------------------
            node_trigger_mode = SDK.CEnumerationPtr(self.node_map.GetNode('TriggerMode'))
            if not SDK.IsAvailable(node_trigger_mode) or not SDK.IsReadable(node_trigger_mode):
                print('Unable to disable trigger mode (node retrieval). Aborting...')
                return False

            node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
            if not SDK.IsAvailable(node_trigger_mode_off) or not SDK.IsReadable(node_trigger_mode_off):
                print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
                return False

            node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

            print('Trigger mode disabled...')

            #--------------------------------------------------------------------------------
            # Set TriggerSelector to AcquisitionStart - This allows trigger to start acquisition itself
            #--------------------------------------------------------------------------------
            node_trigger_selector= SDK.CEnumerationPtr(self.node_map.GetNode('TriggerSelector'))
            if not SDK.IsAvailable(node_trigger_selector) or not SDK.IsWritable(node_trigger_selector):
                print('Unable to get trigger selector (node retrieval). Aborting...')
                return False

            node_trigger_selector_framestart = node_trigger_selector.GetEntryByName('FrameStart')
            if not SDK.IsAvailable(node_trigger_selector_framestart) or not SDK.IsReadable(
                    node_trigger_selector_framestart):
                print('Unable to set trigger selector (enum entry retrieval). Aborting...')
                return False
            node_trigger_selector.SetIntValue(node_trigger_selector_framestart.GetValue())

            print('Trigger selector set to frame start...')

            #--------------------------------------------------------------------------------
            # Set TriggerSource to software
            #--------------------------------------------------------------------------------
            node_trigger_source = SDK.CEnumerationPtr(self.node_map.GetNode('TriggerSource'))
            if not SDK.IsAvailable(node_trigger_source) or not SDK.IsWritable(node_trigger_source):
                print('Unable to get trigger source (node retrieval). Aborting...')
                return False

            node_trigger_source_software = node_trigger_source.GetEntryByName('Software')
            if not SDK.IsAvailable(node_trigger_source_software) or not SDK.IsReadable(
                    node_trigger_source_software):
                print('Unable to set trigger source (enum entry retrieval). Aborting...')
                return False
            node_trigger_source.SetIntValue(node_trigger_source_software.GetValue())
            print('Trigger source set to software...')

            #--------------------------------------------------------------------------------
            # turn trigger mode back on
            #--------------------------------------------------------------------------------
            node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')
            if not SDK.IsAvailable(node_trigger_mode_on) or not SDK.IsReadable(node_trigger_mode_on):
                print('Unable to enable trigger mode (enum entry retrieval). Aborting...')
                return False

            node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())
            print('Trigger mode turned back on...')

            #--------------------------------------------------------------------------------
            # Now I can assign the trigger commmand ptr variable to be used in triggering
            #--------------------------------------------------------------------------------
            self.trigger_command = SDK.CCommandPtr(self.node_map.GetNode('TriggerSoftware'))

            if not SDK.IsAvailable(self.trigger_command) or not SDK.IsWritable(self.trigger_command):
                print('Unable to execute trigger. Aborting...')
                return False
            else:
                print("Trigger command successfully configured!")

            #--------------------------------------------------------------------------------
            # Now I can set aquisition mode to continuous
            #--------------------------------------------------------------------------------
            node_acquisition_mode = SDK.CEnumerationPtr(self.node_map.GetNode('AcquisitionMode'))
            if not SDK.IsAvailable(node_acquisition_mode) or not SDK.IsWritable(node_acquisition_mode):
                print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
                return False

            # Retrieve entry node from enumeration node
            node_acquisition_mode_single_frame = node_acquisition_mode.GetEntryByName('Continuous')
            if not SDK.IsAvailable(node_acquisition_mode_single_frame) or not SDK.IsReadable(node_acquisition_mode_single_frame):
                print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
                return False

            # Set integer value from entry node as new value of enumeration node
            node_acquisition_mode.SetIntValue(node_acquisition_mode_single_frame.GetValue())

            print('Acquisition mode set to continuous...')

            print('Beginning Acquisition...')
            self.device.BeginAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return True

    def Update(self):
        print('FLIR_Module: Update()')
        try:

            # Set exposure
            self.set_exposure() # good
            self.set_gain() # good
            self.set_gamma() # good
            self.set_contrast() # not implemented
            self.set_sharpness() # good
            self.set_saturation() # implemented but not sure of function until we use color camera

        except Exception as e:
            print(e)
            return False

        print('Update complete')

    def Set_Size(self):
        # Even with the example script I am unable to set height and width. I am met with an error that says
        # height and width are unsettable for certain camera models
        """
        print(f'Device Node: {self._Device_Node}')
        Width = SDK.CIntegerPtr(self._Device_Node.GetNode('Width'))
        Height = SDK.CIntegerPtr(self._Device_Node.GetNode('Height'))

        Width_Max = Width.GetMax()
        Height_Max = Height.GetMax()

        print(Width_Max, Height_Max)
        #""""""
        if self._Width<1 and self._Width>(self.Cap.sResolutionRange.iWidthMax-self._Left):
            self._Width = self.Cap.sResolutionRange.iWidthMax-self._Left
        if self._Height<1 and self._Height>(self.Cap.sResolutionRange.iHeightMax-self._Top):
            self._Height = self.Cap.sResolutionRange.iHeightMax-self._Top
        SDK.CameraPause(self.CameraHandle)
        SDK.CameraSetImageResolutionEx(self.CameraHandle, 255, 0, 0, self._Left, self._Top, self._Width, self._Height, 0, 0)
        SDK.CameraPlay(self.CameraHandle)


        node_width = SDK.CIntegerPtr(self._Device_Node.GetNode('Width'))
        print(f"node_width: {node_width.GetValue()}")
        if SDK.IsReadable(node_width) and SDK.IsWritable(node_width):
            width_inc = node_width.GetInc()

            if width_to_set % width_inc != 0:
                width_to_set = int(width_to_set / width_inc) * width_inc

            node_width.SetValue(self._Width)

            print('\tWidth set to {}...'.format(node_width.GetValue()))

        else:
            print('\tUnable to set width; width for sequencer not available on all camera models...')

        # Set height; height recorded in pixels
        node_height = SDK.CIntegerPtr(self._Device_Node.GetNode('Height'))
        if SDK.IsReadable(node_height) and SDK.IsWritable(node_height):
            height_inc = node_height.GetInc()

            if height_to_set % height_inc != 0:
                height_to_set = int(height_to_set / height_inc) * height_inc

            node_height.SetValue(height_to_set)

            print('\tHeight set to %d...' % node_height.GetValue())

        else:
            print('\tUnable to set height; height for sequencer not available on all camera models...')
        """

    def Close(self):
        if self.Device_Info:
            try:
                SDK.CameraUnInit(self.CameraHandle)
                SDK.CameraAlignFree(self.FrameBuffer)
            except:
                return False

    def set_exposure(self):
        print('FLIR_Module: set_exposure()')
        try:
            result = True
            if self.device.ExposureAuto.GetAccessMode() != SDK.RW:
                print('Unable to disable automatic exposure. Aborting...')
                return False

            self.device.ExposureAuto.SetValue(SDK.ExposureAuto_Off)

            if self.device.ExposureMode.GetAccessMode() != SDK.RW:
                print('Unable to set exposure mode. Aborting...')
                return False

            self.device.ExposureMode.SetValue(SDK.ExposureMode_Timed)

            if self.device.ExposureTime.GetAccessMode() != SDK.RW:
                print('Unable to set exposure time. Aborting...')
                return False

            exposure_time_to_set = min(self.device.ExposureTime.GetMax(), self._exposure)
            self.device.ExposureTime.SetValue(exposure_time_to_set)
            print(f'Shutter time set to {exposure_time_to_set}us')

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def set_gain(self):
        print('FLIR_Module: set_gain()')
        try:
            result = True
            if self.device.GainAuto.GetAccessMode() != SDK.RW:
                print('Unable to disable automatic gain. Aborting...')
                return False

            self.device.GainAuto.SetValue(SDK.GainAuto_Off)

            if self.device.Gain.GetAccessMode() != SDK.RW:
                print('Unable to set gain value. Aborting...')
                return False

            gain_to_set = min(self.device.Gain.GetMax(), self._gain)
            # I might need to control for minimum value as well
            self.device.Gain.SetValue(gain_to_set)
            print(f'Gain set to {gain_to_set}')

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def set_gamma(self):
        print('FLIR_Module: set_gamma()')
        try:
            result = True
            if self.device.GammaEnable.GetAccessMode() != SDK.RW:
                return False

            self.device.GammaEnable.SetValue(True)

            if self.device.Gamma.GetAccessMode() != SDK.RW:
                return False

            gamma_to_set = min(self.device.Gamma.GetMax(), self._gamma)
            # I might need to control for minimum value as well
            self.device.Gamma.SetValue(gamma_to_set)
            print(f'Gamma set to {gamma_to_set}')

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def set_contrast(self):
        print('No implementation for contrast adjustment!')

    def set_sharpness(self):
        print('FLIR_Module: set_sharpness()')
        try:
            result = True
            # Sharpness and saturation are advanced controls that require the ISP be enabled and the image processing core be utilized
            # in order to enable ISP, aquistion must be stopped

            # first hault aquisition
            self.device.EndAcquisition()

            # now enable ISP if it is not already
            if self.device.IspEnable.GetAccessMode() != SDK.RW:
                print('Unable to enable ISP. Aborting...')
                return False
            self.device.IspEnable.SetValue(True)

            self.device.SharpeningEnable.SetValue(True)
            if self.device.SharpeningEnable.GetAccessMode() != SDK.RW:
                print('Unable to enable sharpness. Aborting...')
                return False

            self.device.SharpeningEnable.SetValue(True)

            if self.device.SharpeningAuto.GetAccessMode() != SDK.RW:
                print('Unable to disable automatic sharpness. Aborting...')
                return False

            self.device.SharpeningAuto.SetValue(False)

            if self.device.Sharpening.GetAccessMode() != SDK.RW:
                print('Unable to set sharpening value. Aborting...')
                return False

            sharpening_to_set = min(self.device.Sharpening.GetMax(), self._sharpness)
            # I might need to control for minimum value as well
            self.device.Sharpening.SetValue(sharpening_to_set)
            print(f'Sharpness set to {sharpening_to_set}')

            # re enable acquisition
            self.device.BeginAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            self.device.BeginAcquisition()
            result = False

        return result

    def set_saturation(self):
        print('FLIR_Module: set_saturation()')
        try:
            result = True
            if self._Format == 'RGB8':
                # Sharpness and saturation are advanced controls that require the ISP be enabled and the image processing core be utilized
                # in order to enable ISP, aquistion must be stopped

                # first hault aquisition
                self.device.EndAcquisition()

                # now enable ISP if it is not already
                if self.device.IspEnable.GetAccessMode() != SDK.RW:
                    print('Unable to enable ISP. Aborting...')
                    return False
                self.device.IspEnable.SetValue(True)

                self.device.SaturationEnable.SetValue(True)
                if self.device.SaturationEnable.GetAccessMode() != SDK.RW:
                    print('Unable to enable saturation. Aborting...')
                    return False

                self.device.SaturationEnable.SetValue(True)

                if self.device.Saturation.GetAccessMode() != SDK.RW:
                    print('Unable to set saturation value. Aborting...')
                    return False

                saturation_to_set = min(self.device.Saturation.GetMax(), self._saturation)
                # I might need to control for minimum value as well
                self.device.Saturation.SetValue(saturation_to_set)
                print(f'Saturation set to {saturation_to_set}')

                # re enable acquisition
                self.device.BeginAcquisition()

            else:
                print('No saturation adjustment for MONO8 format')

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def start_capture(self):
        print('FLIR_Module: start_capture()')
        self.capture = True
        _thread.start_new_thread(self.capturing_thread, ())

    def end_capture(self):
        print('FLIR_Module: end_capture()')
        self.capture = False

    def capturing_thread(self):
        print('capturing thread starting')

        try:
            if self.device is None:
                print('No device initialized. Exiting!')
                return False

            # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
            node_acquisition_mode = SDK.CEnumerationPtr(self.node_map.GetNode('AcquisitionMode'))
            if not SDK.IsAvailable(node_acquisition_mode) or not SDK.IsWritable(node_acquisition_mode):
                print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
                return False

            # Retrieve entry node from enumeration node
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not SDK.IsAvailable(node_acquisition_mode_continuous) or not SDK.IsReadable(node_acquisition_mode_continuous):
                print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
                return False

            # Retrieve integer value from entry node
            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

            # Set integer value from entry node as new value of enumeration node
            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

            self.device.BeginAcquisition()

            while self.capture:
                image_ptr = self.device.GetNextImage()

                if image_ptr.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_ptr.GetImageStatus())

                else:
                    retrieved_image = image_ptr.GetData().reshape(image_ptr.GetHeight(),image_ptr.GetWidth(), 3 if self._Format == 'RGB8' else 1)

                    # ensure existence of shared memory and if None then create new shared memory
                    if self.sm is None:
                        memory_frame = np.zeros(retrieved_image.shape, dtype=np.uint8)
                        self.sm = shared_memory.SharedMemory(name=f'cam{self._ID}', create=True, size=memory_frame.nbytes)

                    image_buffer = np.ndarray(retrieved_image.shape, dtype=retrieved_image.dtype, buffer=self.sm.buf)

                    # copy image to shared memory buffer
                    np.copyto(image_buffer, retrieved_image)

                    image_ptr.Release()

            self.device.EndAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

    def delete_shared_memory(self):
        try:
            self.sm.close()
            self.sm = None
            return True

        except Exception as e:
            print(e)
            return False

    def trigger(self):
        try:
            #  Retrieve the next image from the trigger
            self.trigger_command.Execute()

            #  Retrieve next received image
            image_ptr = self.device.GetNextImage()

            #  Ensure image completion
            if image_ptr.IsIncomplete():
                print('Image incomplete with image status %d ...' % image_ptr.GetImageStatus())

            else:
                image = image_ptr.GetData().reshape(image_ptr.GetHeight(),image_ptr.GetWidth(), 3 if self._Format == 'RGB8' else 1)

                if self.sm is None:
                    memory_frame = np.zeros(image.shape, dtype=np.uint8)
                    self.sm = shared_memory.SharedMemory(name=f'cam{self._ID}', create=True, size=memory_frame.nbytes)

                image_shape = image.shape
                image_buffer = np.ndarray(image.shape, dtype=image.dtype, buffer=self.sm.buf)

                np.copyto(image_buffer, image)

                image_ptr.Release()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return image_shape
