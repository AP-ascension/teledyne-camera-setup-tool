
import os, sys, multiprocessing

def run_rpc_server():
    os.execv(sys.executable, ["venv/Scripts/python.exe", "FLIR_RPC_Server.py"])


if __name__ == '__main__':

    rpc_server_process = multiprocessing.Process(target=run_rpc_server)
    rpc_server_process.daemon = True
    rpc_server_process.start()

    from Program.Camera import *
'''
I am encountering issues with zombie processes after program termination
Below is some code Jag gave me which may be able to remedy the issue but
this doesnt work as of now

import atexit
import sys
import subprocess

Process = None

def Process_Exit():
    if Process is not None:
        Process.terminate()

atexit.register(Process_Exit)

if __name__ == "__main__":
    Process = subprocess.Popen([sys.executable, 'FLIR_RPC_Server.py'])
    from Program.Camera import *
'''
