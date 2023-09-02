#include <iostream>
#include <vector>
#include <stdint.h>

#include "mincrypt/sha.h"
#include "base.hpp"
#include "magiskboot.hpp"
#include "compress.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/complex.h"

namespace py = pybind11;

void sha1(const char* file) {
    uint8_t sha1[SHA_DIGEST_SIZE];
    auto m = mmap_data(file);
    SHA_hash(m.buf, m.sz, sha1);
    for (uint8_t i : sha1)
        printf("%02x", i);
    printf("\n");
}

void cleanup(void) {
    fprintf(stderr, "Cleaning up...\n");
    unlink(HEADER_FILE);
    unlink(KERNEL_FILE);
    unlink(RAMDISK_FILE);
    unlink(SECOND_FILE);
    unlink(KER_DTB_FILE);
    unlink(EXTRA_FILE);
    unlink(RECV_DTBO_FILE);
    unlink(DTB_FILE);
}

// print support compress/decompress formats
void print_formats() {
    for (int fmt = GZIP; fmt < LZOP; ++fmt) {
        fprintf(stderr, "%s ", fmt2name[(format_t) fmt]);
    }
}

int cpio(py::args args) {
    int ret;
    int argc = args.size();
    char** argv = new char*[argc];

    for (int i = 0; i < argc; ++i) {
        if(!py::isinstance<py::str>(args[i])) {
            delete[] argv;
            throw py::type_error("Value must be str value.");
        }
    }

    for (int i = 0; i < argc; ++i) {
        std::string arg = py::cast<std::string>(args[i]);
        argv[i] = new char[arg.size() + 1];
        std::strcpy(argv[i], arg.c_str());
    }

    // Your logic with argc and argv
    ret = cpio_commands(argc, argv);

    for (int i = 0; i < argc; ++i) {
        delete[] argv[i];
    }
    delete[] argv;

    return ret;
}

int dtb(py::args args) {
    int ret;
    int argc = args.size();
    char** argv = new char*[argc];

    for (int i = 0; i < argc; ++i) {
        if(!py::isinstance<py::str>(args[i])) {
            delete[] argv;
            throw py::type_error("Value must be str value.");
        }
    }

    for (int i = 0; i < argc; ++i) {
        std::string arg = py::cast<std::string>(args[i]);
        argv[i] = new char[arg.size() + 1];
        std::strcpy(argv[i], arg.c_str());
    }

    // Your logic with argc and argv
    ret = dtb_commands(argc, argv);

    for (int i = 0; i < argc; ++i) {
        delete[] argv[i];
    }
    delete[] argv;

    return ret; // Just an example return value
}

PYBIND11_MODULE(magiskboot_pybind, m) {
    m.doc() = "Unpack a android boot image.";
    m.def("unpack", &unpack, "A function unpack a android boot image.",
            py::arg("image"), py::arg("skip_decomp") = (bool)false, py::arg("hdr") = (bool)false);
    m.def("repack", &repack, "A function repack a android boot image.",
            py::arg("src_img"), py::arg("out_img") = NEW_BOOT, py::arg("skip_comp") = (bool)false);
    m.def("sha1", &sha1);
    m.def("cleanup", &cleanup);
    m.def("split", &split_image_dtb);
    m.def("decompress", &decompress);
    m.def("compress", &compress);
    m.def("print_formats", &print_formats);
    m.def("cpio", &cpio);
    m.def("dtb", &dtb);
    m.def("hexpatch", &hexpatch);
}
