# https://github.com/williballenthin/python-ntfs/blob/master/examples/inspect_record/inspect_record.py

"""
Dump stuff related to a single record.
"""
import logging

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "python-ntfs"))
from ntfs.BinaryParser import Mmap
from ntfs.FileMap import FileMap
from ntfs.volume import FlatVolume
from ntfs.filesystem import NTFSFilesystem
from ntfs.mft.MFT import MFTRecord
from ntfs.mft.MFT import Attribute
from ntfs.mft.MFT import ATTR_TYPE
from ntfs.mft.MFT import StandardInformation
from ntfs.mft.MFT import FilenameAttribute
from ntfs.mft.MFT import VolumeInformation
import shutil
#import psutil

FileMap.test()

g_logger = logging.getLogger("ntfs.examples.inspect_record")

# Returns True if found VolumeInformation
def processRecord(record):
    # print("=== MFT Record Header")
    # print(record.get_all_string())

    for attribute in record.attributes():
        # print("=== Attribute Header (type: {:s}) at offset {:s}".format(
        #     Attribute.TYPES[attribute.type()],
        #     hex(attribute.offset())))
        # print(attribute.get_all_string())

        if False:
            pass
        # if attribute.type() == ATTR_TYPE.STANDARD_INFORMATION:
        #     print("=== STANDARD INFORMATION value")
        #     si = StandardInformation(attribute.value(), 0, None)
        #     print(si.get_all_string())

        # elif attribute.type() == ATTR_TYPE.FILENAME_INFORMATION:
        #     print("=== FILENAME INFORMATION value")
        #     fn = FilenameAttribute(attribute.value(), 0, None)
        #     print(fn.get_all_string())

        elif attribute.type() == ATTR_TYPE.VOLUME_INFORMATION:
            print("=== VOLUME INFORMATION value")
            fn = VolumeInformation(attribute.value(), 0, None)
            print(fn.get_all_string())
            return True

    return False

def processRecordFilename(record_filename):
    logging.basicConfig(level=logging.DEBUG)
    #logging.getLogger("ntfs.mft").setLevel(logging.INFO)

    with Mmap(record_filename) as buf:
        record = MFTRecord(buf, 0, None)
        processRecord(record)

def processVolume(volumePath):
    # https://github.com/williballenthin/python-ntfs/blob/master/ntfs/volume/__init__.py

    print("volumePath:", volumePath)
    letterColon = volumePath.rstrip('\\').lstrip('\\').lstrip('.').lstrip('\\')
    #with Mmap(volumePath) as buf:
    with open(volumePath, "rb") as f:
        # https://stackoverflow.com/questions/44873908/how-to-get-total-disk-size-on-windows
        size=shutil.disk_usage(letterColon).total
        #size=psutil.disk_usage(letterColon).total
        buf = FileMap(f, size=size)
        v = FlatVolume(buf, offset=0)
        print("magic:",list(v[3:3+4]))

        # https://github.com/williballenthin/python-ntfs/blob/master/ntfs/filesystem/__init__.py
        fs = NTFSFilesystem(v)
        # root = fs.get_root_directory()
        # g_logger.info("root dir: %s", root)
        # for c in root.get_children():
        #     g_logger.info("  - %s", c.get_name())

        #sys32 = root.get_path_entry("windows\\system32")
        #g_logger.info("sys32: %s", sys32)

        # i = 0
        # while True:
        #     rcrd = fs.get_record(i)
        #     print('proc')
        #     if processRecord(rcrd):
        #         break
        #     i += 1
        #     if i > 10:
        #         break

        rcrd = fs.get_record(3) # Volume info record
        processRecord(rcrd)
        

if __name__ == '__main__':
    import sys
    processVolume(sys.argv[1])
