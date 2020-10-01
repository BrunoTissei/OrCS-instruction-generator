#!/usr/bin/env python3

# Generates dictionary to assign uops.info instructions' strings to icode
# defined by intel's XED. The result is a .py file containing the dictionary
# to be imported and used in a python code.

import os
import argparse
import xml.etree.ElementTree as ET


# Returns parser args
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Generate dictionary python file (istring -> icode)'
    )

    parser.add_argument('--xml',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'instructions.xml'
    )
    parser.add_argument('--arch',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'Architecture (three letters) (e.g. SKL)'
    )
    parser.add_argument('--output',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'Path to python file to be created and used as output.'
    )
    parser.add_argument('--decoder',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'Path decoder.'
    )

    return parser.parse_args()


# Returns whether instruction is available on given architecture or not
def check_if_available(instrNode, arch) -> bool:
    for archNode in instrNode.iter('architecture'):
        if archNode.attrib.get('name', '') == arch:
            return True
    return False


#####################
def main() -> int:
    args = parse_args()
    keys, values = [], []

    f_assembly = open('TMP_ordered_asm.S', 'w')
    root = ET.parse(args.xml)

    FORBIDDEN_EXT = [
        'CLDEMOTE', 'ENQCMD', 'MCOMMIT',
        'MOVDIR', 'PCONFIG', 'RDPRU',
        'SERIALIZE', 'SNP', 'TSX_LDTRK',
        'WAITPKG', 'WBNOINVD'
    ]

    FORBIDDEN_ISA_SET = [ 'BF16_', 'VP2INTERSECT' ]


    # Prints valid assembly code containing all instructions available
    # to the specified architecture (by Andreas Abel - uops.info)
    print('.intel_syntax noprefix', file=f_assembly)
    for instrNode in root.iter('instruction'):
        asm = instrNode.attrib['asm']
        first = True
        suffix = ''

        # Future instruction set extensions
        if instrNode.attrib['extension'] in FORBIDDEN_EXT:
            continue

        if any(x in instrNode.attrib['isa-set'] for x in FORBIDDEN_ISA_SET):
            continue

        # Added condition to check if instruction is available on the
        # specified architecture
        if not check_if_available(instrNode, args.arch):
            continue

        # Each instruction must contain valid operands in order to be
        # assembled properly, these operands types are retrived from
        # xml and renamed to real operands (i.e. registers, memory address)
        # to work with the assembler
        for operandNode in instrNode.iter('operand'):
            operandIdx = int(operandNode.attrib['idx'])

            if operandNode.attrib.get('suppressed', '0') == '1':
                continue

            if not first and not operandNode.attrib.get('opmask', '') == '1':
                asm += ', '
            else:
                asm += ' '
                first = False

            if operandNode.attrib['type'] == 'reg':
                registers = operandNode.text.split(',')
                register = registers[min(operandIdx, len(registers)-1)]
                if not operandNode.attrib.get('opmask', '') == '1':
                    asm += register
                else:
                    asm += '{' + register + '}'
                    if instrNode.attrib.get('zeroing', '') == '1':
                        asm += '{z}'

                if operandNode.attrib.get('implicit', '0') != '1':
                    width = operandNode.attrib.get('width', '16')
                    suffix += '+R' + width

            elif operandNode.attrib['type'] == 'mem':
                memoryPrefix = operandNode.attrib.get('memory-prefix', '')
                if memoryPrefix:
                    asm += memoryPrefix + ' '

                if operandNode.attrib.get('VSIB', '0') != '0':
                    asm += '[' + operandNode.attrib.get('VSIB') + '0]'
                else:
                    asm += '[RAX]'

                memorySuffix = operandNode.attrib.get('memory-suffix', '')
                if memorySuffix:
                    asm += ' ' + memorySuffix

                if operandNode.attrib.get('implicit', '0') != '1':
                    width = operandNode.attrib['width']
                    suffix += '+M' + width

            elif operandNode.attrib['type'] == 'agen':
                agen = instrNode.attrib['agen']
                address = []

                if 'R' in agen: address.append('RIP')
                if 'B' in agen: address.append('RAX')
                if 'I' in agen: address.append('2*RBX')
                if 'D' in agen: address.append('8')

                asm += ' [' + '+'.join(address) + ']'

            elif operandNode.attrib['type'] == 'imm':
                if instrNode.attrib.get('roundc', '') == '1':
                    asm += '{rn-sae}, '
                elif instrNode.attrib.get('sae', '') == '1':
                    asm += '{sae}, '
                width = int(operandNode.attrib['width'])
                if operandNode.attrib.get('implicit', '') == '1':
                    imm = operandNode.text
                else:
                    imm = (1 << (width - 8)) + 1
                asm += str(imm)

                if operandNode.attrib.get('implicit', '0') != '1':
                    width = operandNode.attrib['width']
                    suffix += '+I' + width

            elif operandNode.attrib['type'] == 'relbr':
                asm = '1: ' + asm + '1b'
                if operandNode.attrib.get('implicit', '0') != '1':
                    width = operandNode.attrib['width']
                    suffix += '+Rel' + width

        if not 'sae' in asm:
            if instrNode.attrib.get('roundc', '') == '1':
                asm += ', {rn-sae}'
            elif instrNode.attrib.get('sae', '') == '1':
                asm += ', {sae}'

        # The original code was swapping {load} and {store}
        if asm.startswith('{load}'):
            asm = asm.replace('{load}', '{store}', 1)
        elif asm.startswith('{store}'):
            asm = asm.replace('{store}', '{load}')

        # Resulting dict's keys are the instructions' strings
        keys.append(instrNode.attrib['string'])

        # Writes to assembly (.S file)
        print(asm, file=f_assembly)

    f_assembly.close()

    # In order to obtain icode the following steps must be done:
    # 1. Assemble the .S file using gcc's assembler
    os.system('gcc -c TMP_ordered_asm.S')
    os.system('rm TMP_ordered_asm.S')

    # 2. Use objdump to get hexadecimal from assembly
    assembled = os.popen('objdump -z -M intel -d TMP_ordered_asm.o').readlines()
    assembled = assembled[7:]
    os.system('rm TMP_ordered_asm.o')

    # 3. Fix hex (sometimes an instruction in broken into 2 lines)
    hex_result, ihex = [], ''
    for asm in reversed(assembled):
        line = asm[:-1].split('\t')
        ihex = line[1].replace(' ', '') + ihex
        if len(line) == 3:
            hex_result.append(ihex)
            ihex = ''

    # 4. Use xed to get icode from hexadecimal
    while len(hex_result) > 0:
        input_hex = hex_result.pop()
        command = f'{args.decoder} -64 -chip SKYLAKE {input_hex}'
        result = os.popen(command).readlines()
        values.append(result[0][:-1])

    # 5. Generate file containing keys (string) -> values (icode)
    f_mapping = open(args.output, 'w')
    
    print('instructions = (', file = f_mapping)
    lines = []
    for k, v in zip(keys, values):
        lines.append(f'\t{{ instr = "{k}"; icode = "{v}"; }}')
    print(',\n'.join(lines), file = f_mapping)
    print(');', file = f_mapping)

    f_mapping.close()

    return 0
