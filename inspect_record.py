import sys
import struct
try:
    from hexdump import hexdump
except:
    try:
        from .hexdump import hexdump
    except:
        hexdump = print
from collections import namedtuple
import os
import ctypes

ntfs = '<3s8sHBH3s2sB2sHH2s2s4s4sQQQB3sBQ4s'
ntfs_ = namedtuple('ntfs', 'x86JumpInstructionToTheBootLoaderRoutine systemID bytesPerSector sectorsPerCluster reservedSectors reserved0 reserved10 mediaDescriptor reserved20 sectorsPerTrack numberOfHeads notUsed0 notUsed10 notUsed20 reserved30 totalSectors mftOffset mftMirrOffset private_clustersPerMFTFileRecord private_clustersPerMFTIndexRecord notUsed40 volumeSerialNumber notUsed50') # https://stackoverflow.com/questions/11461125/is-there-an-elegant-way-to-use-struct-and-namedtuple-instead-of-this
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
struct NTFS {
  // For more info see ntfsdoc-0.6/files/boot.html since this is $Boot. Also see https://www.cse.scu.edu/~tschwarz/coen252_07Fall/Lectures/NTFS.html where it says "Table 2: BPB and extended BPB fields on NTFS volumes".
  char x86JumpInstructionToTheBootLoaderRoutine[3]; // ntfsdoc-0.6/files/boot.html
  char systemID[8]; // "NTFS    "
  uint16_t bytesPerSector;
  uint8_t sectorsPerCluster;
  uint16_t reservedSectors; // "Reserved" value, "must be 0" (probably for forwards compatibility)
  char reserved0[3]; // "Reserved" value, "must be 0"
  char reserved10[2]; // "Reserved" value, "must be 0"
  MediaDescriptor mediaDescriptor;
  char reserved20[2]; // "Reserved" value, "must be 0"
  uint16_t sectorsPerTrack; // "Not used or checked by NTFS." according to the cse.scu.edu website but is something on ntfsdoc-0.6/files/boot.html
  uint16_t numberOfHeads; // "Not used or checked by NTFS." according to the cse.scu.edu website but is something on ntfsdoc-0.6/files/boot.html
  char notUsed0[2]; // "Not used or checked by NTFS."
  char notUsed10[2]; // "Not used or checked by NTFS."
  char notUsed20[4]; // "Not used or checked by NTFS."
  char reserved30[4]; // "Reserved" value, "must be 0"  // "Usually 80 00 80 00" + "A value of 80 00 00 00 has been seen on a USB thumb drive which is formatted with NTFS under Windows XP. Note this is removable media and is not partitioned, the drive as a whole is NTFS formatted." ( ntfsdoc-0.6/files/boot.html )
  uint64_t totalSectors; // "Number of sectors in the volume" ( ntfsdoc-0.6/files/boot.html )
  uint64_t mftOffset; // In clusters (LCNs)  // "LCN of VCN 0 of the $MFT" ( ntfsdoc-0.6/files/boot.html )
  uint64_t mftMirrOffset; // "Logical cluster number for the copy of the Master File Table (File $MFTmir)"  // "LCN of VCN 0 of the $MFTMirr" ( ntfsdoc-0.6/files/boot.html )
  uint8_t _clustersPerMFTFileRecord; // "If the value is less than 7F, then this number is the clusters per Index Buffer. Otherwise, 2x, with x being the negative of this number, is the size of the file record." ( https://www.cse.scu.edu/~tschwarz/coen252_07Fall/Lectures/NTFS.html ) aka "This can be negative, which means that the size of the MFT/Index record is smaller than a cluster. In this case the size of the MFT/Index record in bytes is equal to 2^(-1 * Clusters per MFT/Index record). So for example if Clusters per MFT Record is 0xF6 (-10 in decimal), the MFT record size is 2^(-1 * -10) = 2^10 = 1024 bytes." ( ntfsdoc-0.6/files/boot.html )
  char notUsed30[3]; // "Not used or checked by NTFS."
  size_t bytesPerMFTFileRecord() const { // Returns the actual amount obeying the above description.
    if ((int8_t)_clustersPerMFTFileRecord < 0) {
      uint8_t exp = -1*(int8_t)_clustersPerMFTFileRecord;
      return 1 << exp; // Is the same as 2 to the power of `exp`. (std::pow is only really good for floating point numbers)  // This is now in bytes instead of clusters because it is smaller than a single cluster usually.
    }
    return _clustersPerMFTFileRecord * bytesPerCluster();
  }
  uint8_t _clustersPerMFTIndexRecord; // "Clusters per Index Buffer. If the value is less than 7F, then this number is the clusters per Index Buffer. Otherwise, 2x, with x being the negative of this number, is the size of the file record." ( https://www.cse.scu.edu/~tschwarz/coen252_07Fall/Lectures/NTFS.html ) aka "This can be negative, which means that the size of the MFT/Index record is smaller than a cluster. In this case the size of the MFT/Index record in bytes is equal to 2^(-1 * Clusters per MFT/Index record). So for example if Clusters per MFT Record is 0xF6 (-10 in decimal), the MFT record size is 2^(-1 * -10) = 2^10 = 1024 bytes." ( ntfsdoc-0.6/files/boot.html )
  char notUsed40[3]; // "Not used or checked by NTFS."
  size_t bytesPerMFTIndexRecord() const { // Returns the actual amount obeying the above description.
    if ((int8_t)_clustersPerMFTIndexRecord < 0) {
      uint8_t exp = -1*(int8_t)_clustersPerMFTIndexRecord;
      return 1 << exp;
    }
    return _clustersPerMFTIndexRecord * bytesPerCluster();
  }
  uint64_t volumeSerialNumber;
  char notUsed50[4]; // "Not used or checked by NTFS."
"""

mftRecord = '<4sHHQHHHHLLQH2sL4048s'
mftRecord_ = namedtuple('mftRecord', 'magicNumber updateSequenceOffset numEntriesInFixupArray logFileSequenceNumber sequenceNumber hardLinkCount offsetToFirstAttribute flags usedSizeOfMFTEntry allocatedSizeOfMFTEntry fileReferenceToTheBase_FILE_record nextAttributeID padding10 numberOfThisMFTRecord attributesAndFixupValue')
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
// An entry within the MFT.
struct MFTRecord {
  char magicNumber[4]; // "FILE" (or, if the entry is unusable, we would find it marked as "BAAD").
  uint16_t updateSequenceOffset;
  uint16_t numEntriesInFixupArray; // Fixup array = update sequence (synonymns).  // This is the number of entries where an entry is a single 16 bit value.
  uint64_t logFileSequenceNumber; // (LSN)  // "Each MFT record is addressed by a 48 bit MFT entry value [is simply the 0-based index of this record; an "entry index"].The first entry has address 0. Each MFT entry has a 16 bit sequence number that is incremented when the entry is allocated. MFT entry value and sequence number combined yield 64b [bit] file reference address."  // "This is changed every time the record is modified." ( ntfsdoc-0.6/concepts/file_record.html )
  uint16_t sequenceNumber; // Says how many times this entry has been used.  // "N.B. The increment (skipping zero) is done when the file is deleted." + "N.B. If this is set to zero it is left as zero." ( ntfsdoc-0.6/concepts/file_record.html )
  uint16_t hardLinkCount; // "The hard link count is the number of directory entries that reference this record."
  uint16_t offsetToFirstAttribute; // *useful*
  MFTEntryFlags flags;
  uint32_t usedSizeOfMFTEntry;
  uint32_t allocatedSizeOfMFTEntry;
  uint64_t fileReferenceToTheBase_FILE_record; // "MFT entries could be larger than fit into the normal space. In this case, the MFT entry will start in the base MFT record and continued in an extension record." If the file reference to the base file entry is 0x 00 00 00 00 00 00 00 00 then this is a base record. Were it not so, then this field would contain a reference to the base MFT record.
  uint16_t nextAttributeID; // This is the "next attribute ID" in the sense that it is the next attribute ID to place into this MFTRecord *if* you are adding a new attribute entry I think. Since the attributes are in ascending order by ID apparently. Anyway, main point is that numAttributes() is based on this.       // ntfsdoc-0.6/concepts/attribute_id.html : {"
  // Next Attribute Id
  //     The Attribute Id that will be assigned to the next Attribute added to this MFT Record.
  //     N.B. Incremented each time it is used.
  //     N.B. Every time the MFT Record is reused this Id is set to zero.
  //     N.B. The first instance number is always 0.
  // "}
  char padding10[2]; // "Align to 4B boundary" on Windows XP
  // [I think this is this but not sure:] The "entry value" or "entry number" for this MFTRecord. This is just the 0-based index of this record basically.
  uint32_t numberOfThisMFTRecord; // On Windows XP
  char attributesAndFixupValue[0x1000-0x30]; // Attributes and fixup value
"""

attributeBase = '<LLBBHHH'
attributeBase_ = namedtuple('attributeBase', 'typeIdentifier attributeLength nonResidentFlag lengthOfName offsetToName flags attributeIdentifier')
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
enum AttributeTypeIdentifier: uint32_t {
  STANDARD_INFORMATION = 0x10,
  ATTRIBUTE_LIST = 0x20,
  FILE_NAME = 0x30,
  VOLUME_VERSION = 0x40, // Windows NT
  OBJECT_ID = 0x40, // Windows 2000
  SECURITY_DESCRIPTOR = 0x50,
  VOLUME_NAME = 0x60,
  VOLUME_INFORMATION = 0x70,
  DATA = 0x80,
  INDEX_ROOT = 0x90,
  INDEX_ALLOCATION = 0xA0,
  BITMAP = 0xB0,
  SYMBOLIC_LINK = 0xC0, // Windows NT
  REPARSE_POINT = 0xC0, // Windows 2000
  EA_INFORMATION = 0xD0,
  EA = 0xE0,
  PROPERTY_SET = 0xF0, // Windows NT
  LOGGED_UTILITY_STREAM = 0x100 // Windows 2000
};

// Notes: "Only the data attribute can be compressed, or sparse, and only when it is non-resident." + "Although the compression flag is stored in the header, it does not affect the size of the header." ( ntfsdoc-0.6/concepts/attribute_header.html )
enum AttributeFlags: uint16_t {
  AttributeFlags_Compressed = 0x0001,
  AttributeFlags_Encrypted = 0x4000,
  AttributeFlags_Sparse = 0x8000
};

struct AttributeBase {
  AttributeTypeIdentifier typeIdentifier; // "The attribute type identifier determines also the layout of the contents."
  uint32_t attributeLength; // (determines the location of next attribute)
  uint8_t nonResidentFlag;
  uint8_t lengthOfName; // (Optional, if a name is present then this is a "named attribute" ( ntfsdoc-0.6/concepts/attribute_header.html ))
  uint16_t offsetToName; // (Optional, same situation as the above)
  AttributeFlags flags;
  uint16_t attributeIdentifier; // "Each attribute has a unique identifier" ( ntfsdoc-0.6/concepts/attribute_header.html ) + "Every Attribute in every FILE Record has an Attribute Id. This Id is unique within the FILE Record and is used to maintain data integrity." ( ntfsdoc-0.6/concepts/attribute_id.html )
  
  // Returns the attribute name or nullptr if this is not a named attribute.
  ArrayWithLength<uint16_t> name() const {
    if (lengthOfName != 0) {
      assert(offsetToName != 0);
      return {(uint16_t*)((uint8_t*)this + offsetToName), lengthOfName};
    }
    else {
      //assert(offsetToName == 0);
      return {nullptr, 0};
    }
  }
};
"""

volumeInformation = "<8sccH4s"
volumeInformation_ = namedtuple('volumeInformation', 'maybeAlwaysZero0 majorVersionNumber minorVersionNumber flags maybeAlwaysZero10')
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
enum VolumeInformationFlags: uint16_t {
  Dirty = 0x0001, // "When the Dirty Flag is set, Windows NT must perform the chkdsk /F command on the volume when it next boots."
  ResizeLogFile = 0x0002,
  UpgradeOnMount = 0x0004,
  MountedOnNT4 = 0x0008,
  DeleteUSN_underway = 0x0010,
  RepairObjectIds = 0x0020,
  ModifiedByChkdsk = 0x8000
};
// ntfsdoc-0.6/files/volume.html -> ntfsdoc-0.6/attributes/volume_information.html
// "Indicates the version and the state of the volume."
struct VolumeInformation {
  char maybeAlwaysZero0[8];

  // Version numbers:
  // Operating System	NTFS Version
  // Windows NT		1.2
  // Windows 2000	3.0
  // Windows XP		3.1
  char majorVersionNumber;
  char minorVersionNumber;
  
  VolumeInformationFlags flags;
  char maybeAlwaysZero10[4];
};
"""
# https://stackoverflow.com/questions/58136441/decompose-a-combined-intflag-into-its-individual-flags
import enum
class VolumeInformationFlags(enum.IntFlag):
  Dirty = 0x0001
  ResizeLogFile = 0x0002
  UpgradeOnMount = 0x0004
  MountedOnNT4 = 0x0008
  DeleteUSN_underway = 0x0010
  RepairObjectIds = 0x0020
  ModifiedByChkdsk = 0x8000

  # More flags from https://dfir.ru/2019/01/19/ntfs-today/ :
  # {"
  # Here is a full list of volume flags found in Windows 10:
  # 0x1: a volume is corrupt (dirty);
  # 0x2: need to resize the $LogFile journal;
  # 0x4: need to upgrade the volume version;
  # 0x8: the object IDs, the quotas, and the USN journal metadata can be corrupt (this flag is set by Windows NT 4.0);
  # 0x10: need to delete the USN journal;
  # 0x20: need to repair the object IDs;
  # 0x40: a volume is corrupt and it caused a bug check;
  # 0x80: persistent volume state: no tunneling cache, the short file names creation is disabled;
  # 0x100: need to run the full Chkdsk scan;
  # 0x200: need to run the proactive scan;
  # 0x400: persistent volume state: the TxF feature is disabled;
  # 0x800: persistent volume state: the volume scrub is disabled;
  # 0x1000: do not create the corruption log file ($Verify and $Corrupt);
  # 0x2000: persistent volume state: the heat gathering is disabled;
  # 0x4000: this was a system volume during the Chkdsk scan;
  # 0x8000: a volume was modified by the Chkdsk scan.
  # As you can see, Microsoft ran out of possible volume flags, because the $VOLUME_INFORMATION flags are stored in two bytes.
  # "}
  VolumeCorruptBugCheck = 0x40
  PersistentVolumeState_NoTunnelingCacheAndShortFileNamesDisabled = 0x80
  NeedFullChkdsk = 0x100
  NeedProactiveScan = 0x200
  PersistentVolumeState_TxFDisabled = 0x400
  PersistentVolumeState_VolumeScrubDisabled = 0x800
  DoNotCreateVerifyAndCorruptSpecialFiles = 0x1000
  PersistentVolumeState_HeatGatheringDisabled = 0x2000
  WasASystemVolumeDuringChkdsk = 0x4000

residentAttributeBesidesBase = "<LHBc"
residentAttributeBesidesBase_ = namedtuple('residentAttribute', 'base sizeOfContent offsetToContent indexedFlag padding') # `base` must be added manually as a field while constructing this from a struct.unpack call.
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
// Resident = in this MFT. These have a different structure from non-resident ones.
struct ResidentAttribute {
  AttributeBase base;
  uint32_t sizeOfContent;
  uint16_t offsetToContent;
  uint8_t indexedFlag; // ntfsdoc-0.6/concepts/attribute_header.html
  char padding[1]; // ntfsdoc-0.6/concepts/attribute_header.html

  std::pair<AttributeContent, std::optional<MyDataRuns> /*placeholder, will be empty*/> content(.../*<--placeholder for std::visit, ignore this*/) const {
    uint8_t* contentPtr = (uint8_t*)this + offsetToContent;
    switch (base.typeIdentifier) {
    case STANDARD_INFORMATION:
      return std::make_pair((StandardInformation*)contentPtr, std::optional<MyDataRuns>());
    case FILE_NAME:
      return std::make_pair((FileName*)contentPtr, std::optional<MyDataRuns>());
    case VOLUME_INFORMATION:
      return std::make_pair((VolumeInformation*)contentPtr, std::optional<MyDataRuns>());
    default:
      throw UnhandledValue();
    }
  }
};
"""

nonResidentAttributeBesidesBase = "<QQHHLQQQ"
nonResidentAttributeBesidesBase_ = namedtuple('nonResidentAttribute', 'base startingVirtualClusterNumberOfTheDataRuns endingVirtualClusterNumberOfTheDataRuns offsetToTheRunList compressionUnitSize unused allocatedSizeOfTheAttributeContent actualSizeOfTheAttributeContent initializedSizeOfTheAttributeContent') # `base` must be added manually as a field while constructing this from a struct.unpack call.
# https://github.com/sbond75/ntfsAnalysisLib/blob/master/main.cpp :
"""
// "non-resident attributes need to describe an arbitrary number of cluster runs, consecutive clusters that they occupy."
struct NonResidentAttribute {
  AttributeBase base;
  uint64_t startingVirtualClusterNumberOfTheDataRuns;
  uint64_t endingVirtualClusterNumberOfTheDataRuns;
  uint16_t offsetToTheRunList; // aka the "[list of stuff that points to the] data runs"
  uint16_t compressionUnitSize; // "[Actual?] compression unit size = 2^x clusters [where x is probably compressionUnitSize]. 0 implies uncompressed" ( ntfsdoc-0.6/concepts/attribute_header.html )
  uint32_t unused;
  uint64_t allocatedSizeOfTheAttributeContent; // "This is the attribute size rounded up to the cluster size" ( ntfsdoc-0.6/concepts/attribute_header.html )
  uint64_t actualSizeOfTheAttributeContent;
  uint64_t initializedSizeOfTheAttributeContent; // "Compressed data size." ( ntfsdoc-0.6/concepts/attribute_header.html )

  Pair<AttributeContentWithFreer, std::optional<MyDataRuns>> content(size_t limitToLoad, bool* out_moreNeeded, ssize_t* out_more, int fd, const NTFS* ntfs) const;
};
"""

def bytesPerMFTFileRecord(ntfsheader):
    # https://stackoverflow.com/questions/1375897/how-to-get-the-signed-integer-value-of-a-long-in-python , https://docs.python.org/3/library/ctypes.html
    number = ntfsheader.private_clustersPerMFTFileRecord & 0xFF
    signed_number = ctypes.c_byte(number).value
    
    if signed_number < 0:
        exp = -1 * signed_number
        return 1 << exp
    return ntfsheader.private_clustersPerMFTFileRecord * bytesPerCluster(ntfsheader)

def bytesPerSector(header):
    return header.bytesPerSector

def sectorsPerCluster(header):
    return header.sectorsPerCluster

def bytesPerCluster(header):
    return bytesPerSector(header) * sectorsPerCluster(header)

def mftOffset(header):
    return header.mftOffset

def mftOffsetInBytes(header):
    return mftOffset(header) * bytesPerCluster(header)

def fixupArray(mftrec, buf):
    return struct.unpack(f'<{mftrec.numEntriesInFixupArray}H', buf[mftrec.updateSequenceOffset : mftrec.updateSequenceOffset + mftrec.numEntriesInFixupArray * 2]) # 2 = sizeof(uint16_t)

def updateSequenceNumber(mftrec, buf):
    return struct.unpack('<H', buf[mftrec.updateSequenceOffset : mftrec.updateSequenceOffset + 2])[0]

def applyFixup(mftrec, buf, bytesPerSector):
    arr = fixupArray(mftrec, buf)
    sectorIterator = 0 + bytesPerSector - 2 # 2 = sizeof(uint16_t)
    usn = updateSequenceNumber(mftrec, buf)
    outBuf = bytearray(buf) # https://stackoverflow.com/questions/66984217/change-byte-array-buffer-with-python
    for val in arr:
        if sectorIterator > mftrec.usedSizeOfMFTEntry:
            #print("applyFixup: sectorIterator is past usedSizeOfMFTEntry")
            break

        valPtr = sectorIterator
        toCheck = struct.unpack('<H', buf[valPtr:valPtr+2])[0]
        print(f"applyFixup: {toCheck} should be usn {usn}");
        assert(toCheck == usn);
        print(f"  {toCheck} -> {val}");
        outBuf[valPtr:valPtr+2] = struct.pack('<H', val)
        sectorIterator += bytesPerSector

    # Re-unpack
    mftrec = mftRecord_._make(struct.unpack(mftRecord, outBuf))
    
    return mftrec, outBuf

def numAttributes(mftrec, buf):
    retval = mftrec.nextAttributeID - 1

    # Find end marker
    counter = 0
    size = struct.calcsize(attributeBase)
    seek = mftrec.offsetToFirstAttribute
    attrbuf = buf[seek : seek + size]
    currentAttr = attributeBase_._make(struct.unpack(attributeBase, attrbuf))
    while (currentAttr.typeIdentifier != 0xffffffff # The end marker for attribute list
           ):
        if not (counter < retval):
            #print("numAttributes: !( counter < retval)\n");
            break

        seek += currentAttr.attributeLength
        attrbuf = buf[seek : seek + size]
        currentAttr = attributeBase_._make(struct.unpack(attributeBase, attrbuf))
        counter += 1
        
    print(f"numAttributes: counter {counter}, retval {retval}");
    #assert(counter == retval);
    #return retval;
    
    return counter

def residentAttribute(attrBase, buf):
    size = struct.calcsize(attributeBase)
    size2 = struct.calcsize(residentAttributeBesidesBase)
    noBase = struct.unpack(residentAttributeBesidesBase, buf[size : size + size2])
    attr = residentAttributeBesidesBase_._make((attrBase, *noBase))
    return attr

def nonResidentAttribute(attrBase, buf):
    size = struct.calcsize(attributeBase)
    size2 = struct.calcsize(nonResidentAttributeBesidesBase)
    noBase = struct.unpack(nonResidentAttributeBesidesBase, buf[size : size + size2])
    attr = nonResidentAttributeBesidesBase_._make((attrBase, *noBase))
    return attr

def makeAttribute(attrBase, attrbuf):
    return {0: residentAttribute(attrBase, attrbuf),
            1: nonResidentAttribute(attrBase, attrbuf)
            }[attrBase.nonResidentFlag]

def attributes(mftrec, buf):
    ret = []
    size = struct.calcsize(attributeBase)
    seek = mftrec.offsetToFirstAttribute
    attrbuf = buf[seek : seek + size]
    currentAttr = attributeBase_._make(struct.unpack(attributeBase, attrbuf))
    assert mftrec.offsetToFirstAttribute != 0 # TODO: what if there are no attributes? this is a failsafe: (maybe return empty array instead but I'm not sure if 0 means this)

    numAttrs = numAttributes(mftrec, buf)
    for i in range(numAttrs):
        attr = makeAttribute(currentAttr, buf[seek:])
        
        ret.append((attr, buf[seek:]))
        print(f"MFTRecord::attributes: found attribute with type {hex(currentAttr.typeIdentifier)} and offset {hex(seek)} from the start of the MFTRecord")
        
        seek += currentAttr.attributeLength
        attrbuf = buf[seek : seek + size]
        currentAttr = attributeBase_._make(struct.unpack(attributeBase, attrbuf))

    return ret
    
def getFirstMFTRecord(f, ntfsheader):
    offset = mftOffsetInBytes(ntfsheader)
    f.seek(offset, os.SEEK_SET)
    size = struct.calcsize(mftRecord)
    buf = f.read(size)
    mftrec = mftRecord_._make(struct.unpack(mftRecord, buf))

    # Apply fixup
    mftrec, buf = applyFixup(mftrec, buf, bytesPerSector(ntfsheader))
    
    return mftrec, buf

# mftrecordNum is the number to get
# FIXME: this doesn't consider if the MFT is itself in data runs..?
def getMFTRecord(f, mftrecordNum, ntfsheader):
    bytesPerMFTFileRecord_ = bytesPerMFTFileRecord(ntfsheader)
    offset = mftOffsetInBytes(ntfsheader) + bytesPerMFTFileRecord_ * mftrecordNum

    f.seek(offset, os.SEEK_SET)
    size = struct.calcsize(mftRecord)
    buf = f.read(size)
    mftrec = mftRecord_._make(struct.unpack(mftRecord, buf))

    # Apply fixup
    mftrec, buf = applyFixup(mftrec, buf, bytesPerSector(ntfsheader))
    
    return mftrec, buf

VOLUME_INFORMATION = 0x70

def processVolume(volumePath):
    # https://github.com/williballenthin/python-ntfs/blob/master/ntfs/volume/__init__.py

    print("volumePath:", volumePath)
    #with Mmap(volumePath) as buf:
    with open(volumePath, "rb") as f:
        size = struct.calcsize(ntfs)
        buf = f.read(size)
        header = ntfs_._make(struct.unpack(ntfs, buf))
        hexdump(buf); print(header)
        firstrec, firstbytes = getFirstMFTRecord(f, header)
        hexdump(firstbytes); #print(firstrec)

        #attributeBase_._make(struct.unpack(

        print(map(lambda x: x[0], attributes(firstrec, firstbytes)))

        volinforec, volinforecbytes = getMFTRecord(f, 3 # volume information
                                  , header)
        volinfoattrs = attributes(volinforec, volinforecbytes)
        #hexdump(volinforecbytes)
        print(map(lambda x: x[0], volinfoattrs))

        for x in volinfoattrs:
            attr, buf = x
            if attr.base.typeIdentifier == VOLUME_INFORMATION:
                assert isinstance(attr, residentAttributeBesidesBase_), "Must be resident" # (with base actually)
                content = buf[attr.offsetToContent : attr.offsetToContent + attr.sizeOfContent]
                print(len(content))
                if len(content) < 16:
                    assert len(content) == 12
                    # Need some more for maybeAlwaysZero10
                    content += b'\0\0\0\0'
                volinfo = volumeInformation_._make(struct.unpack(volumeInformation, content))
                print('@@@@@@@@@@@@',volinfo)
                flags = VolumeInformationFlags(volinfo.flags)
                print(flags)
                # # https://stackoverflow.com/questions/58136441/decompose-a-combined-intflag-into-its-individual-flags
                # flags = [flag for flag in VolumeInformationFlags if flag in flags]
                # # for flag in VolumeInformationFlags:
                # #     #print(flag.value)
                # #     print(flag.value & volinfo.flags == flag.value)
                # # flags = [flag for flag in VolumeInformationFlags if flag & flags == flag]

                # # Now find unknown flags
                # # .....
                
                # print(flags)
                return flags
        return None

if __name__ == '__main__':
    import sys
    processVolume(sys.argv[1])
