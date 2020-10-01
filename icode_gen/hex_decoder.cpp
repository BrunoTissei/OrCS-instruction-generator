#include <iostream>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <cassert>

extern "C" {
#include "xed/xed-interface.h"
}

unsigned int hex_to_dec(char x) {
    if (x >= '0' && x <= '9')
        return x - '0';
    return (toupper(x) - 'A') + 10U;
}

unsigned int ascii_to_hex(const char *src,
                          xed_uint8_t *dst,
                          unsigned int max_bytes)
{
    const unsigned int len = strlen(src);
    memset(dst, 0, max_bytes);

    for (unsigned int p = 0, i = 0; i < len / 2; ++i, p += 2)
        dst[i] = (xed_uint8_t) (hex_to_dec(src[p]) * 16 + hex_to_dec(src[p+1]));
    return len/2;
}

std::string get_operands(xed_decoded_inst_t *xedd) {
    const xed_inst_t* xi = xed_decoded_inst_inst(xedd);
    unsigned int noperands = xed_inst_noperands(xi);

    std::string result = "";
    for (unsigned int i = 0; i < noperands; ++i) {
        const xed_operand_t* op = xed_inst_operand(xi, i);
        xed_operand_enum_t op_name = xed_operand_name(op);

        std::string ops = "";

        switch (op_name) {
            case XED_OPERAND_AGEN:
                break;

            case XED_OPERAND_MEM0:
            case XED_OPERAND_MEM1: {
                ops += "M";
                break;
            }

            // pointer and rel
            case XED_OPERAND_PTR:   
            case XED_OPERAND_RELBR: {
                ops += "Rel";
                break;
            }

            // immediates
            case XED_OPERAND_IMM0:
            case XED_OPERAND_IMM1: {
                ops += "I";
                break;
            }
            case XED_OPERAND_REG0:
            case XED_OPERAND_REG1:
            case XED_OPERAND_REG2:
            case XED_OPERAND_REG3:
            case XED_OPERAND_REG4:
            case XED_OPERAND_REG5:
            case XED_OPERAND_REG6:
            case XED_OPERAND_REG7:
            case XED_OPERAND_REG8:
            case XED_OPERAND_BASE0:
            case XED_OPERAND_BASE1: {
                ops += "R";
                break;
            }
            default: 
                assert(0);      
        }

        auto vis = xed_operand_operand_visibility(op);
        if (vis == XED_OPVIS_EXPLICIT && ops.size() > 0) {
            result += "+";
            xed_uint_t bits = xed_decoded_inst_operand_length_bits(xedd, i);
            ops += std::to_string(bits);
            result += ops;
        }
    }

    return std::string(xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(xedd))) + result;
}

int main(int argc, char** argv) {
    xed_state_t dstate;
    xed_decoded_inst_t xedd;

    xed_tables_init();
    xed_state_zero(&dstate);

    dstate.mmode = XED_MACHINE_MODE_LEGACY_32;
    dstate.stack_addr_width = XED_ADDRESS_WIDTH_32b;

    xed_uint_t first_argv = 1;
    xed_bool_t already_set_mode = 0;
    xed_chip_enum_t chip = XED_CHIP_INVALID;

    xed_uint_t argcu = (xed_uint_t) argc;

    for (xed_uint_t i = 1; i < argcu; ++i) {
        if (strcmp(argv[i], "-64") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LONG_64;
            first_argv++;
        } else if (strcmp(argv[i], "-16") == 0) {
            assert(already_set_mode == 0);
            already_set_mode = 1;
            dstate.mmode=XED_MACHINE_MODE_LEGACY_16;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        } else if (strcmp(argv[i], "-s16") == 0) {
            already_set_mode = 1;
            dstate.stack_addr_width=XED_ADDRESS_WIDTH_16b;
            first_argv++;
        } else if (strcmp(argv[i], "-chip") == 0) {
            assert(i+1 < argcu);
            chip = str2xed_chip_enum_t(argv[i+1]);
            assert(chip != XED_CHIP_INVALID);
            first_argv+=2;
        }
    }

    assert(first_argv == argcu - 1);

    std::string hex(argv[first_argv]);

    xed_decoded_inst_zero_set_mode(&xedd, &dstate);
    xed_decoded_inst_set_input_chip(&xedd, chip);

    unsigned char itext[XED_MAX_INSTRUCTION_BYTES];
    xed_uint_t bytes = ascii_to_hex(hex.c_str(), itext, XED_MAX_INSTRUCTION_BYTES);
    xed_decode(&xedd, XED_REINTERPRET_CAST(const xed_uint8_t*, itext), bytes);

    std::cout << get_operands(&xedd) << std::endl;
    return 0;
}
