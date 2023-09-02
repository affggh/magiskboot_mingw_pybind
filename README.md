# MagiskBoot - Boot Image Modification Tool
The most complete tool for unpacking and repacking Android boot images.    
pybind11 on magiskboot on mingw32/64

**Note**: This is a minimal (dirty) copy of topjohnwu's [MagiskBoot](https://github.com/topjohnwu/Magisk/tree/master/native/src/boot).

## Documentation
- [MagiskBoot Documentation](https://topjohnwu.github.io/Magisk/tools.html#magiskboot)

## Build
- Using MSYS2 `mingw32/64` environment with `mingw-w64-i686/x86_64-toolchain` packages group, `python3`, LLVM version 14 and up, run `make pybind` command. (`magiskboot_pybind.[target].pyd` will appear in the `out` folder).

## What's changed:
- `cpio` action `extract` with no paramaters to `ramdisk` folder in current directory.
   * it creates `cpio` file to allow mode/uid/gid changes in Windows (with `sync` or `pack`)
- new `cpio` action `sync` that synchronize incpio entries with `ramdisk` directory (as new cpio). Any changes will be captured and dumped to `incpio`.
- new `cpio` action `pack` as follows: `cpio pack [-c <config>] <infolder> <outcpio>`
   * if `<config>` is undefined `cpio` is looked-up instead.

## For Windows
- There's some UBs/SFs that needs to be addressed (test and report).
- Tested and working operations are limited.