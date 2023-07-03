# Based on https://poe.com/Sage

import os
import string
import tkinter as tk
#import win32api
#import win32file
import tkinter.messagebox as messagebox
import inspect_record
import sys

def get_partitions():
    """Get list of partition names on Windows"""
    partitions = []
    for letter in string.ascii_uppercase:
        try:
            if os.path.isdir(letter + ":\\"):
                #device_path = win32file.GetVolumeNameForVolumeMountPoint(f"{letter}:\\")
                #partitions.append(device_path)

                # https://stackoverflow.com/questions/6522644/how-to-open-disks-in-windows-and-read-data-at-low-level
                device_path = f"\\\\.\\{letter}:"
                partitions.append(device_path)
        except PermissionError as e:
            print(e)
            continue
    return partitions

# # https://stackoverflow.com/questions/4188326/in-python-how-do-i-check-if-a-drive-exists-w-o-throwing-an-error-for-removable
# import ctypes
# import itertools
# import os
# import string
# import platform
# def get_available_drives():
#     if 'Windows' not in platform.system():
#         return []
#     drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
#     return list(itertools.compress(string.ascii_uppercase,
#                map(lambda x:ord(x) - ord('0'), bin(drive_bitmask)[:1:-1])))

labelRes = None
def open_partition(device_path):
    """Open a partition for reading"""
    # disk_fd = os.open(device_path, os.O_RDONLY | os.O_BINARY)
    # data = os.read(disk_fd, 512)
    # os.close(disk_fd)
    # return data

    flags = inspect_record.processVolume(device_path)
    
    labelRes.config(text="Flags: " + str(flags))
    #labelRes.visible = True

def on_select(device_path):
    """Event handler for dropdown selection"""
    #device_path = event.widget.get()
    print(device_path)
    try:
        data = open_partition(device_path)
        # Do something with the data
        
    except PermissionError as e:
        messagebox.showerror("Error", "Permission denied. You probably need to re-open this program as administrator.\n\n" + str(e))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        messagebox.showerror("Error", str(e) + "\n\n" + tb)

if __name__ == '__main__':
    # Create Tkinter window and widgets
    root = tk.Tk()
    root.title("Partition Viewer")

    label = tk.Label(root, text="Select a partition to view:")
    #label.pack()
    label.grid(row=0, column=0)

    labelRes = tk.Label(root, text="")
    #labelRes.pack()
    labelRes.grid(row=2, column=0)
    
    if len(sys.argv) > 1:
        part = sys.argv[1]
        if part[0] in string.ascii_uppercase or part[0] in string.ascii_lowercase: # C:
            part = f"\\\\.\\{part}{'' if part.endswith(':') else ':'}"
        open_partition(part)
        partitions = []
    else:
        partitions = get_partitions()
    selected_partition = tk.StringVar()
    selected_partition.set(partitions[0])
    dropdown = tk.OptionMenu(root, selected_partition, *partitions, command=on_select)
    #dropdown.pack()
    dropdown.grid(row=1, column=0)

    root.mainloop()
