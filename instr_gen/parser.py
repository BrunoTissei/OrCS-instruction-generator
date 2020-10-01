import math
import xml.etree.ElementTree as ET

from collections import defaultdict

from instr_gen.config import Config
from instr_gen.instruction import Instruction


CYCLES = [
    'cycles', 'cycles_addr', 'cycles_mem',
    'max_cycles', 'max_cycles_addr',
    'min_cycles', 'min_cycles_addr',
    'cycles_same_reg'
]


# Parse measurement data from xml ans fills args dict
def parse_measurements(args: dict, arch_node) -> bool:
    done = False

    for measure_node in arch_node.iter('measurement'):
        args['throughput']   = measure_node.attrib.get('TP')
        args['ports']        = measure_node.attrib.get('ports')
        args['num_uops'] = int(measure_node.attrib.get('uops', '0'))

        mn_lat, mx_lat = math.inf, -math.inf

        for lat_node in measure_node.iter('latency'):
            for cycle in CYCLES:
                if cycle in lat_node.attrib:
                    mn_lat = min(mn_lat, int(lat_node.attrib[cycle]))
                    mx_lat = max(mx_lat, int(lat_node.attrib[cycle]))

        if mn_lat != math.inf:
            args['min_lat'] = mn_lat
            args['max_lat'] = mx_lat
        else:
            args['min_lat'] = math.nan
            args['max_lat'] = math.nan

        done = True

    return done


# Parse instructions xml
def parse(xml_path: str, config: Config) -> defaultdict:
    root = ET.parse(xml_path)
    icodes = {}

    for instr_node in root.iter('instruction'):
        extension = instr_node.attrib['extension']
        if not config.check_extension(extension):
            continue

        # Args for the current instruction
        args = {}
        args['name'] = instr_node.attrib.get('string')
        args['iform'] = instr_node.attrib.get('iform')
        args['extension'] = extension

        ok = False

        # Gets data from specified architecture
        for arch_node in instr_node.iter('architecture'):
            if arch_node.attrib.get('name', '-') == config.arch:
                ok = ok or parse_measurements(args, arch_node)

        if not ok:
            continue

        if math.isnan(args['min_lat']):
            continue

        args['icode'] = config.icode_mapping[args['name']]

        if args['icode'] in icodes:
            continue
        icodes[args['icode']] = 1

        instr = Instruction(args, config.ports)
        config.add_instruction(instr)

    return config.instr_groups
