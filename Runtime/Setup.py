from cx_Freeze import setup,Executable

setup(
    name = 'Camera Setup',
    version = '1.0',
    description = 'Camera Setup',
    author = 'Name',
    author_email = 'Email',
    options={
        'build_exe': {
            'packages': ['os', 'time', '_thread', 'cv2', 'PIL', 'pathlib', 'datetime', 'numpy', 'requests', 'Crypto', 'platform', 'ctypes', 'threading', 'sqlite3', 'tkinter'],
            'includes': [],
        }
    },
    executables = [Executable(script='Camera.py', icon="Icon.ico", base="Win32GUI")]
)

#   python setup.py build