import magiskboot_pybind as mb

import os, sys
import shutil
#import subprocess
import zipfile
from hashlib import sha1
import mmap

class NoVerbose:
    def write(*args):
        pass

    def flush():
        pass

class Patch:
    def __init__(self, keepverity=False, keepforceencrypt=False, patchvbmetaflag=False, recoverymode=False, legacysar=False, debug=False):
        # init defaults
        self.debug = debug
        #self.magiskboot = "./magiskboot"
        self.magiskboot = mb
        self.KEEPVERITY = keepverity
        self.KEEPFORCEENCRYPT = keepforceencrypt
        self.PATCHVBMETAFLAG = patchvbmetaflag
        self.RECOVERYMODE = recoverymode
        self.LEGACYSAR = legacysar
        self.CHROMEOS = False              # Only pixel C need sign with futility
        # self.EXERETURNCODE = 0
        #if os.name == 'nt':
        #    self.creationflags = subprocess.CREATE_NO_WINDOW
        #else:
        #    self.creationflags = 0
        #self.env = {
        #                'KEEPVERITY': self.bool2str(self.KEEPVERITY),
        #                'KEEPFORCEENVRYPT': self.bool2str(self.KEEPFORCEENCRYPT),
        #                'PATCHVBMETAFLAG': self.bool2str(self.PATCHVBMETAFLAG),
        #                'RECOVERYMODE': self.bool2str(self.RECOVERYMODE)
        #            }
        self.setenv()
    
    #def setmagiskboot(self, loc):
    #    self.magiskboot = loc
    def getsha1(self, file):
        fsize = os.stat(file).st_size
        with open(file, 'rb') as f:
            with mmap.mmap(f.fileno(), fsize, access=mmap.ACCESS_READ, offset=0) as m:
                return sha1(m).hexdigest()

    def getprop(self, file, key):
        with open(file, 'r') as f:
            for i in iter(f.readline, ""):
                if i.startswith(key) and (not i.startswith("#")):
                    return i.split("=")[1]
        return ""

    def bool2str(self, var):
        if var:
            return "true"
        else:
            return "false"

    def setenv(self):
        '''
        Set environments
        '''
        os.environ['KEEPVERITY'] = self.bool2str(self.KEEPVERITY)
        os.environ['KEEPFORCEENCRYPT'] = self.bool2str(self.KEEPFORCEENCRYPT)
        os.environ['PATCHVBMETAFLAG'] = self.bool2str(self.PATCHVBMETAFLAG)
        os.environ['RECOVERYMODE'] = self.bool2str(self.RECOVERYMODE)
        os.environ['LEGACYSAR'] = self.bool2str(self.LEGACYSAR)
        try:
            if os.environ['PREINITDEVICE']:
                pass
        except: # prefix some issue
            os.environ['PREINITDEVICE'] = "/data/adb/magisk"
        self.PREINITDEVICE = os.environ['PREINITDEVICE']
    
    def patchboot(self, infile):

        if not type(infile) == str:
            raise TypeError("infile type must be file path str")
        
        config = []

        # unpack boot image
        sys.stdout.write("- Unpacking boot image\n")
        #retcode = self.execv([self.magiskboot, "unpack", infile])
        retcode = self.magiskboot.unpack(infile)
        if retcode == 0:
            pass
        elif retcode == 1:
            sys.stderr.write("! Unsupported/Unknown image format\n")
            return False
        elif retcode == 2:
            sys.stdout.write("- ChromeOS boot image detected\n")
            self.CHROMEOS = True
        else:
            sys.stderr.write("! Unable to unpack boot image\n")
            return False
        
        # check ramdisk status
        sys.stdout.write("- Checking ramdisk status\n")
        if not os.access("ramdisk.cpio", os.F_OK):
            retcode = 0    # Stock A only legacy SAR, or some Android 13 GKIs
            SKIP_BACKUP = '#'
        else:
            #  retcode = self.execv([self.magiskboot, "cpio", "ramdisk.cpio", "test"])
            retcode = self.magiskboot.cpio("ramdisk.cpio", "test")
            SKIP_BACKUP = ''
        SHA1 = ""
        status = retcode
        if (status & 3) == 0:
            sys.stdout.write("- Stock boot image detected\n")
            #SHA1 = self.exegetout([self.magiskboot, "sha1", "%s" %infile])
            SHA1 = self.getsha1(infile)
            shutil.copyfile(infile, "stock-boot.img")
        elif (status & 3) == 1:
            sys.stdout.write("- Magisk patched boot image detected\n")
            if os.getenv("SHA1") == "":
                #SHA1 = self.magiskboot.cpio("ramdisk.cpio", "sha1")
                SHA1 = self.getsha1("ramdisk.cpio")
            retcode = self.magiskboot.cpio ("ramdisk.cpio", "restore")
            shutil.copyfile("ramdisk.cpio", "ramdisk.cpio.orig")
            if os.path.isfile("stock-boot.img"):
                os.remove("stock-boot.img")
        elif (status & 3) == 2:
            sys.stderr.write("! Boot image patched by unsupported programs\n",
                             "! Please restore back to stock boot image\n")
            return False
        
        # Work around custom legacy Sony /init -> /(s)bin/init_sony : /init.real setup
        INIT = "init"
        if not status&4 == 0:
            INIT = "init.real"
        
        PREINITDEVICE = ""
        if os.access("config.orig", os.F_OK):
            os.chmod("config.orig", 0o644)
            SHA1 = self.getprop("config.orig", "SHA1")
            PREINITDEVICE = self.getprop("config.orig", "PREINITDEVICE")
            os.unlink("config.orig")
        
        # Ramdisk Patches
        sys.stdout.write("- Patching ramdisk\n")
        with open("config", "w") as f:
            f.write("KEEPVERITY=%s\n" %self.bool2str(self.KEEPVERITY))
            f.write("KEEPFORCEENCRYPT=%s\n" %self.bool2str(self.KEEPFORCEENCRYPT))
            f.write("PATCHVBMETAFLAG=%s\n" %self.bool2str(self.PATCHVBMETAFLAG))
            f.write("RECOVERYMODE=%s\n" %self.bool2str(self.RECOVERYMODE))
            if not PREINITDEVICE == "":
                sys.stdout.write("- Pre-init storage partition: %s\n" %PREINITDEVICE)
                f.write("PREINITDEVICE=%s\n" %PREINITDEVICE)
            if not SHA1=="":
                f.write("SHA1=%s\n" %SHA1)
        
        skip32 = False
        skip64 = False

        if not os.path.isfile("magisk32"):
            skip32 = True
        else:
            retcode = self.magiskboot.compress("xz", "magisk32", "magisk32.xz")
            #retcode = self.execv([self.magiskboot, "compress=xz", "magisk32", "magisk32.xz"])
        if not os.path.isfile("magisk64"):
            skip64 = True
        else:
            retcode = self.magiskboot.compress("xz", "magisk64", "magisk64.xz")
            #retcode = self.execv([self.magiskboot, "compress=xz", "magisk64", "magisk64.xz"])
        if os.path.isfile("stub.apk"):
            retcode = self.magiskboot.compress("xz", "stub.apk", "stub.xz")


        cmd = ["ramdisk.cpio",
               "add 0750 %s magiskinit" %INIT,
               "mkdir 0750 overlay.d",
               "mkdir 0750 overlay.d/sbin",
               "patch",
               SKIP_BACKUP + " backup ramdisk.cpio.orig",
               "mkdir 000 .backup",
               "add 000 .backup/.magisk config"]
        if os.access("stub.xz", os.F_OK):
            cmd.append("add 0644 overlay.d/sbin/stub.xz stub.xz")
        if not skip32: cmd.insert(7, "add 0644 overlay.d/sbin/magisk32.xz magisk32.xz")
        if not skip64: cmd.insert(7, "add 0644 overlay.d/sbin/magisk64.xz magisk64.xz")

        #retcode = self.execv(cmd)
        retcode = self.magiskboot.cpio(*cmd)
        try:
            os.remove("ramdisk.cpio.orig")
            os.remove("config")
        except:
            pass
        if os.path.isfile("magisk32.xz"): os.remove("magisk32.xz")
        if os.path.isfile("magisk64.xz"): os.remove("magisk64.xz")
        if os.path.isfile("stub.xz"): os.remove("stub.xz")

        # Binary Patches
        for dt in ["dtb", "kernel_dtb", "extra"]:
            if os.path.isfile(dt):
                if not self.magiskboot.dtb(dt, "test") == 0:
                    sys.stderr.write("! Boot image %s was patched by old (unsupported) Magisk\n" %dt,
                                     "! Please try again with *unpatched* boot image\n")
                    return False
                if self.magiskboot.dtb(dt, "patch") == 0:
                    sys.stdout.write("- Patch fstab in boot image %s dt" %dt)
        
        if os.path.isfile("kernel"):
            # Remove Samsung RKP
            retcode = self.magiskboot.hexpatch("kernel",
                                    "49010054011440B93FA00F71E9000054010840B93FA00F7189000054001840B91FA00F7188010054",
                                    "A1020054011440B93FA00F7140020054010840B93FA00F71E0010054001840B91FA00F7181010054")
            # Remove Samsung defex
            # Before: [mov w2, #-221]   (-__NR_execve)
            # After:  [mov w2, #-32768]
            retcode = self.magiskboot.hexpatch("kernel",
                                    "821B8012", "E2FF8F12")
            # Force kernel to load rootfs
            # skip_initramfs -> want_initramfs
            retcode = self.magiskboot.hexpatch("kernel",
                                    "736B69705F696E697472616D667300", "77616E745F696E697472616D667300")
        
        # Repack & Flash
        sys.stdout.write("- Repacking boot image\n")
        if not self.magiskboot.repack(infile) == 0:
            sys.stderr.write("! Unable to repack boot image\n")
            return False
        
        if self.CHROMEOS:
            sys.stderr.write("- Not support sign with futility on python yet...")
            return False

        return True
    
    def parseApk(self, filename:str, arch:str):
        #filename = RUNDIR + os.sep + "prebuilt" + os.sep + self.magisk + ".apk"
        def returnMagiskVersion(buf):
            v = "Unknow"
            l = buf.decode('utf_8').split("\n")
            for i in l:
                if not i.find("MAGISK_VER=") == -1:
                    v = i.split("=")[1].strip("'")
                    break
            return v
        def rename(n:str):
            if n.startswith("lib") and n.endswith(".so"):
                n = n.replace("lib", "").replace(".so", "")
            return n
        if not os.access(filename, os.F_OK):
            return False
        else:
            try:
                f = zipfile.ZipFile(filename, 'r')
            except:
                print("apk文件打开错误，不能识别为zip压缩包\n"
                      "请删除[%s]后更换镜像源重新下载" %filename)
                return
            l = f.namelist() # l equals list
            tl = []  # tl equals total get list
            for i in l:
                if i.startswith("assets/") or \
                   i.startswith("lib/"):
                    tl.append(i)

            buf = f.read("assets/util_functions.sh")
            mVersion = returnMagiskVersion(buf)
            print("- Parse Magisk Version : " + mVersion)
            for i in tl:
                if i.startswith("assets"):
                    f.extract(i, "tmp")
                else:
                    if arch == "arm64":
                        if i.startswith("lib/arm64-v8a/") and i.endswith(".so"):
                                f.extract(i, "tmp")
                    elif arch == "arm":
                        if i.startswith("lib/armeabi-v7a/") and i.endswith(".so"):
                                f.extract(i, "tmp")
                    elif arch == "x86_64":
                        if i.startswith("lib/x86_64/") and i.endswith(".so"):
                                f.extract(i, "tmp")
                    elif arch == "x86":
                        if i.startswith("lib/x86/") and i.endswith(".so"):
                                f.extract(i, "tmp")
            for i in tl:
                if not i.startswith("assets"):
                    if arch == "arm64" and not os.access("libmagisk32.so", os.F_OK):
                        if i == "lib/armeabi-v7a/libmagisk32.so":
                            f.extract("lib/armeabi-v7a/libmagisk32.so", "tmp")
                    elif arch == "x86_64" and not os.access("libmagisk32.so", os.F_OK):
                        if i == "lib/x86/libmagisk32.so":
                            f.extract("lib/armeabi-v7a/libmagisk32.so", "tmp")
            f.close()
            shutil.move("tmp/assets/", "assets/")
            if os.access("assets/stub.apk", os.F_OK):
                shutil.move("assets/stub.apk", "stub.apk")
            for root, dirs, files in os.walk("tmp"):
                for file in files:
                    if file.endswith(".so"):
                        shutil.move(root+os.sep+file, rename(os.path.basename(file)))
            if os.access("magiskpolicy", os.F_OK):
                shutil.move("magiskpolicy", "assets/magiskpolicy")
            shutil.rmtree("tmp")
            return True
    def cleanup(self):
        rmlist = [
            "busybox",
            "config",
            "magisk32",
            "magisk64",
            "magisk64",
            "magiskinit",
            "magiskboot",
            "stub.apk",
        ]
        for i in rmlist:
            if os.access(i, os.F_OK): os.unlink(i)
        self.magiskboot.cleanup()
        if os.access("assets", os.F_OK):
            shutil.rmtree("assets")

if __name__ == '__main__':
    import argparse

    support_arch = ["arm64", "arm", "x86_64", "x86"]
    parser = argparse.ArgumentParser(
        prog="patcher",
        usage="./patcher -m [magisk.apk] -i [boot.img] [-v]",
        description="This program is used to patch magisk to boot.img."
    )
    helpmsg = "aceept true/false."
    parser.add_argument("-v,--verbose", default=False, type=bool, nargs=None, help="defined this to allow verbose output.", required=False, dest='verbose')
    parser.add_argument("--keep-forceencrypt", default='False', type=str, help=helpmsg, required=False)
    parser.add_argument("--keep-verity", default='False', type=str, help=helpmsg, required=False)
    parser.add_argument("--patch-vbmetaflag", default='False', type=str, help=helpmsg, required=False)
    parser.add_argument("--recovery-mode", default='False', type=str, help=helpmsg, required=False)
    parser.add_argument("-m,--magisk", required=True, type=str, help="Magisk.apk path", dest="magisk")
    parser.add_argument("-a,--arch", required=False, choices=support_arch, default="arm64", help=f"Arch choice, support {support_arch}", dest="arch")
    parser.add_argument("-b,--boot", required=True, type=str, dest="boot")

    args = parser.parse_args()
    # print(args)
    if not args.verbose:
        sys.stderr = NoVerbose()
    
    p = Patch(
        args.keep_verity,
        args.keep_forceencrypt,
        args.patch_vbmetaflag,
        args.recovery_mode,
        False,
        False,
    )
    if os.access("magiskinit", os.F_OK):
        print("- Detect magiskinit exist, remove first.")
        p.cleanup()
    
    p.parseApk(
        args.magisk,
        args.arch
    )
    
    p.patchboot(
        args.boot
    )

    p.cleanup()

    # exit anyway
    sys.exit(0)
    