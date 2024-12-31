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
        else:
            camera_module.delete_shared_memory()

        camera_module.config(ID=SN, format=format)
        return True

    except Exception as e:
        print(e)
        return False

def trigger():
    global camera_module
    try:
        return camera_module.trigger()
    except Exception as e:
        print(e)
        return False

def delete_shared_memory():
    global camera_module
    camera_module.delete_shared_memory()

def set_exposure(microseconds):
    global camera_module
    return camera_module.config(exposure=microseconds)

def set_gain(gain):
    global camera_module
    return camera_module.config(gain=gain)

def set_gamma(gamma):
    global camera_module
    return camera_module.config(gamma=gamma)

def set_contrast(contrast):
    global camera_module
    return camera_module.config(contrast=contrast)

def set_sharpness(sharpness):
    global camera_module
    return camera_module.config(sharpness=sharpness)

def set_saturation(saturation):
    global camera_module
    return camera_module.config(saturation=saturation)

def set_width(width):
    global camera_module
    return camera_module.config(width=width)

def set_height(height):
    global camera_module
    return camera_module.config(height=height)

def set_left(left):
    global camera_module
    return camera_module.config(left=left)

def set_top(top):
    global camera_module
    return camera_module.config(top=top)

def set_format(format):
    global camera_module
    return camera_module.config(format=format)

def get_config():
    global camera_module
    return camera_module.get_config()

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

rpc_server.Method(trigger)

rpc_server.Method(get_config)
rpc_server.Method(get_info)
rpc_server.Method(get_size)

rpc_server.Method(get_parameter_ranges)

rpc_server.Start()
