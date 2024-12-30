import PySpin as SDK
import numpy as np
import _thread
from multiprocessing import shared_memory

class FLIRModule:
    def __init__(self):
        self._Config = ['ID', 'exposure', 'gain', 'gamma', 'contrast', 'sharpness', 'saturation', 'width', 'height', 'left', 'top', 'format']
        self._ID = False
        self._ID_Old = False
        self._exposure = 25000
        self._gain = 8
        self._gamma = 100
        self._contrast = 100
        self._sharpness = 0
        self._saturation = 50
        self._width = 8000
        self._height = 8000
        self._left = 100
        self._top = 1000
        self._format = 'Mono8'
        self._filter = False # FLIR does have support for various filters

        self.system = None
        self.device_list = None
        self.device = None
        self.device_info = None
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
    def formats():
        return ['Mono8', 'RGB8Packed']

    def Info(self):
        return self.device_info

    def Size(self):
        width_node = SDK.CIntegerPtr(self.node_map.GetNode('Width'))
        height_node = SDK.CIntegerPtr(self.node_map.GetNode('Height'))
        if self.device_info:
            return [width_node.GetMax(), height_node.GetMax()]
        else:
            return False

    def Config_Get(self):
        return [self._exposure, self._gain, self._gamma, self._contrast, self._sharpness, self._saturation, self._width, self._height, self._left, self._top]


    def Config(self, **Input):
        result = True
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

                result &= self.set_format()
                result &= self.set_size()

            else:
                print("No camera connected! Exiting")
                return False

        result &= self.Update()

        return result

    def Connect(self):
        if self.system is None:
            self.system = SDK.System.GetInstance()
        self.device_list = self.system.GetCameras()

        num_cameras = self.device_list.GetSize()

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

            device_serial_number = SDK.CStringPtr(device.GetTLDeviceNodeMap().GetNode("DeviceSerialNumber"))

            if SDK.IsReadable(device_serial_number):
                device_serial_number = device_serial_number.GetValue()

                # Cameras are initalized with IDs. They use this ID to reference a database
                # where the camera serial number can be found. I am using a dictionary to mimic
                # the database in the meantime.
                if self._ID==device_serial_number:
                    self.device = device

                    self.device.Init()
                    self.node_map = self.device.GetNodeMap()
                    self.device_info = [self.device.DeviceModelName.GetValue(), self.device.DeviceSerialNumber.GetValue()]

                    return True

        return False

    def configure_trigger(self):
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

            #--------------------------------------------------------------------------------
            # turn trigger mode back on
            #--------------------------------------------------------------------------------
            node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')
            if not SDK.IsAvailable(node_trigger_mode_on) or not SDK.IsReadable(node_trigger_mode_on):
                print('Unable to enable trigger mode (enum entry retrieval). Aborting...')
                return False

            node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())

            #--------------------------------------------------------------------------------
            # Now I can assign the trigger commmand ptr variable to be used in triggering
            #--------------------------------------------------------------------------------
            self.trigger_command = SDK.CCommandPtr(self.node_map.GetNode('TriggerSoftware'))

            if not SDK.IsAvailable(self.trigger_command) or not SDK.IsWritable(self.trigger_command):
                print('Unable to execute trigger. Aborting...')
                return False

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

            self.device.BeginAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return True

    def Update(self):
        result = True
        try:
            result &= self.set_exposure() # good
            result &= self.set_gain() # good
            result &= self.set_gamma() # good
            #result &= self.set_contrast()
            result &= self.set_sharpness() # good
            result &= self.set_saturation() # implemented but not sure of function until we use color camera

        except Exception as e:
            print(e)
            return False

        return result

    def set_format(self, force_mono=False):
        result = True
        try:
            # first hault aquisition
            self.device.EndAcquisition()

            node_pixel_format = SDK.CEnumerationPtr(self.node_map.GetNode('PixelFormat'))
            if SDK.IsAvailable(node_pixel_format) and SDK.IsWritable(node_pixel_format):

                # Retrieve the desired entry node from the enumeration node
                node_pixel_format_selectable = SDK.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono8' if force_mono else self._format))
                if SDK.IsAvailable(node_pixel_format_selectable) and SDK.IsReadable(node_pixel_format_selectable):

                    # Retrieve the integer value from the entry node
                    pixel_format_mono8 = node_pixel_format_selectable.GetValue()

                    # Set integer as new value for enumeration node
                    node_pixel_format.SetIntValue(pixel_format_mono8)

                    # re enable acquisition
                    self.device.BeginAcquisition()

                else:
                    print(f'Pixel format ({self._format}) not available...')
                    if not force_mono:
                        self.set_format(True)
                    else:
                        result = False

            else:
                print('Pixel format not available...')
                if not force_mono:
                    self.set_format(True)
                else:
                    result = False


        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return result

    def set_size(self):
        result = True
        try:
            self.device.EndAcquisition()

            # set pixel format
            if self._format in self.formats():
                node_pixel_format = SDK.CEnumerationPtr(self.node_map.GetNode('PixelFormat'))
                if SDK.IsAvailable(node_pixel_format) and SDK.IsWritable(node_pixel_format):
                    node_pixel_format_entry_ptr = SDK.CEnumEntryPtr(node_pixel_format.GetEntryByName(self._format))
                    if SDK.IsAvailable(node_pixel_format_entry_ptr) and SDK.IsReadable(node_pixel_format_entry_ptr):

                        pixel_format_int_value = node_pixel_format_entry_ptr.GetValue() # get format's corresponding int value
                        node_pixel_format.SetIntValue(pixel_format_int_value) # set int as value for enumeration node

                        print('Pixel format set to %s...' % node_pixel_format.GetCurrentEntry().GetSymbolic())

                    else:
                        print(f'Pixel format {self._format} not available...')
                        result = False

                else:
                    print(f'Pixel format, {self._format}, not available...')
                    result = False


            #----------------------------------------------------------------------------------------
            x_offset_node = SDK.CIntegerPtr(self.node_map.GetNode('OffsetX'))
            y_offset_node = SDK.CIntegerPtr(self.node_map.GetNode('OffsetY'))

            # set x offset
            if SDK.IsAvailable(x_offset_node) and SDK.IsWritable(x_offset_node):

                x_offset_to_set = round(self._left / x_offset_node.GetInc()) * x_offset_node.GetInc() # round to nearest increment value
                x_offset_to_set = min(x_offset_node.GetMax(), x_offset_to_set) # less then max value
                x_offset_to_set = max(x_offset_node.GetMin(), x_offset_to_set) # more then min value

                x_offset_node.SetValue(x_offset_to_set)
                self._left = x_offset_node.GetValue()

                print('Offset X set to %i...' % x_offset_node.GetValue())

            else:
                print('Offset X not available...')
                result = False

            # set y offset
            if SDK.IsAvailable(y_offset_node) and SDK.IsWritable(y_offset_node):

                y_offset_to_set = round(self._top / y_offset_node.GetInc()) * y_offset_node.GetInc() # round to nearest increment value
                y_offset_to_set = min(y_offset_node.GetMax(), y_offset_to_set) # less then max value
                y_offset_to_set = max(y_offset_node.GetMin(), y_offset_to_set) # more then min value

                y_offset_node.SetValue(y_offset_to_set)
                self._top = y_offset_node.GetValue()

                print('Offset Y set to %i...' % y_offset_node.GetValue())

            else:
                print('Offset Y not available...')
                result = False

            #----------------------------------------------------------------------------------------
            width_node = SDK.CIntegerPtr(self.node_map.GetNode('Width'))
            height_node = SDK.CIntegerPtr(self.node_map.GetNode('Height'))

            # set image width
            if SDK.IsAvailable(width_node) and SDK.IsWritable(width_node):

                width_to_set = round(self._width / width_node.GetInc()) * width_node.GetInc() # round to nearest increment value
                width_to_set = min(width_node.GetMax(), width_to_set) # less then max value
                width_to_set = max(width_node.GetMin(), width_to_set) # more then min value

                width_node.SetValue(width_to_set)
                self._width = width_node.GetValue()

                print('Width set to %i...' % width_node.GetValue())
            else:
                print('Width not available...')
                result = False

            # set image height
            if SDK.IsAvailable(height_node) and SDK.IsWritable(height_node):

                height_to_set = round(self._height / height_node.GetInc()) * height_node.GetInc() # round to nearest increment value
                height_to_set = min(height_node.GetMax(), height_to_set) # less then max value
                height_to_set = max(height_node.GetMin(), height_to_set) # more then min value

                height_node.SetValue(height_to_set)
                self._height = height_node.GetValue()

                print('Height set to %i...' % height_node.GetValue())

            else:
                print('Height not available...')
                result = False


            self.device.BeginAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return result

    def Close(self):
        if self.Device_Info:
            try:
                SDK.CameraUnInit(self.CameraHandle)
                SDK.CameraAlignFree(self.FrameBuffer)
            except:
                return False

    def set_exposure(self):
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
        result = True
        try:
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
        result = True
        try:
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
        return True

    def set_sharpness(self):
        result = True
        try:
            # Sharpness and saturation are advanced controls that require the ISP be enabled and the image processing core be utilized
            # in order to enable ISP, aquistion must be stopped AND format set to mono
            #self.set_format(force_mono=True)
            # first hault aquisition
            self.device.EndAcquisition()

            # now enable ISP if it is not already
            if self._format != 'RGB8Packed':
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


            # re enable acquisition and reset format
            #self.set_format()
            self.device.BeginAcquisition()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            self.device.BeginAcquisition()
            result = False

        return result

    def set_saturation(self):
        result = True
        try:
            if self._format == 'RGB8Packed':
                # Sharpness and saturation are advanced controls that require the ISP be enabled and the image processing core be utilized
                # in order to enable ISP, aquistion must be stopped

                # first set format to mono and hault aquisition
                #self.set_format(force_mono=True)
                self.device.EndAcquisition()

                # now enable ISP if it is not already
                '''
                if self.device.IspEnable.GetAccessMode() != SDK.RW:
                    print('Unable to enable ISP. Aborting...')
                    return False
                self.device.IspEnable.SetValue(True)
                '''
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

                # re enable acquisition and reset format
                #self.set_format()
                self.device.BeginAcquisition()

            else:
                print('No saturation adjustment for MONO8 format')

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def start_capture(self):
        self.capture = True
        _thread.start_new_thread(self.capturing_thread, ())

    def end_capture(self):
        self.capture = False

    def capturing_thread(self):

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
                    print(self._format)
                    retrieved_image = image_ptr.GetData().reshape(image_ptr.GetHeight(),image_ptr.GetWidth(), 3 if self._format == 'RGB8Packed' else 1)

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
                image = image_ptr.GetData().reshape(image_ptr.GetHeight(),image_ptr.GetWidth(), 3 if self._format == 'RGB8Packed' else 1)

                if self.sm is None:
                    memory_frame = np.zeros(image.shape, dtype=np.uint8)
                    self.sm = shared_memory.SharedMemory(name=f'cam{self._ID}', create=True, size=memory_frame.nbytes)

                image_shape = image.shape
                image_buffer = np.ndarray(image.shape, dtype=image.dtype, buffer=self.sm.buf)

                np.copyto(image_buffer, image)

                image_ptr.Release()

        except SDK.SpinnakerException as ex:
            print('Error: %s' % ex)
            self.Config()
            return False

        return image_shape
