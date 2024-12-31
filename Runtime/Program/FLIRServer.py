from RPC import Server
from FLIRModule import FLIRModule

import sys

process_number = int(sys.argv[1])
print(process_number)

rpc_server = Server((61010 + process_number), '127.0.0.1')
camera_module = None

def config(SN, format):
    global camera_module
    try:
        if camera_module is None:
            camera_module = FLIRModule()
        
        camera_module.Config(ID=SN, format=format)
        camera_module.delete_shared_memory()
        
        return True

    except Exception as e:
        print(e)
        return False

def trigger():
    '''
    This method will take a single image and save it to the shared memory.

    Returns:
    image_shape: tuple
    '''
    global camera_module
    try:
        if camera_module is None:
            config()

        dim = camera_module.trigger()

        return dim
    except Exception as e:
        print(e)
        return False

# clear the shared memory
def delete_shared_memory():
    global camera_module
    camera_module.delete_shared_memory()

def set_exposure(microseconds):
    global camera_module
    return camera_module.Config(exposure=microseconds)

def set_gain(gain):
    global camera_module
    return camera_module.Config(gain=gain)

def set_gamma(gamma):
    global camera_module
    return camera_module.Config(gamma=gamma)

def set_contrast(contrast):
    global camera_module
    return camera_module.Config(contrast=contrast)

def set_sharpness(sharpness):
    global camera_module
    return camera_module.Config(sharpness=sharpness)

def set_saturation(saturation):
    global camera_module
    return camera_module.Config(saturation=saturation)

def set_width(width):
    global camera_module
    return camera_module.Config(width=width)

def set_height(height):
    global camera_module
    return camera_module.Config(height=height)

def set_left(left):
    global camera_module
    return camera_module.Config(left=left)

def set_top(top):
    global camera_module
    return camera_module.Config(top=top)

def set_format(format):
    global camera_module
    return camera_module.Config(format=format)


def start_video_stream():
    global camera_module

    if camera_module is None:
        config()

    camera_module.start_capture()

def end_video_stream():
    global camera_module

    if camera_module is None:
        config()

    camera_module.end_capture()

def get_config():
    global camera_module
    return camera_module.Config_Get()

def get_info():
    global camera_module
    return camera_module.Info()

def get_size():
    global camera_module
    return camera_module.Size()

def get_parameter_ranges():
    global camera_module
    return camera_module.get_parameter_ranges()


rpc_server.Method(config)

rpc_server.Method(set_exposure)
rpc_server.Method(set_gain)
rpc_server.Method(set_gamma)
rpc_server.Method(set_contrast)
rpc_server.Method(set_sharpness)
rpc_server.Method(set_saturation)
rpc_server.Method(set_width)
rpc_server.Method(set_height)
rpc_server.Method(set_left)
rpc_server.Method(set_top)
rpc_server.Method(set_format)

rpc_server.Method(delete_shared_memory)

rpc_server.Method(start_video_stream)
rpc_server.Method(end_video_stream)

rpc_server.Method(trigger)

rpc_server.Method(get_config)
rpc_server.Method(get_info)
rpc_server.Method(get_size)

rpc_server.Method(get_parameter_ranges)

rpc_server.Start()
