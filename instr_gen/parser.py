import math
import xml.etree.ElementTree as ET

from collections import defaultdict
from instr_gen.instruction import Instruction


CYCLES = [
    'cycles', 'cycles_addr', 'cycles_mem',
    'max_cycles', 'max_cycles_addr',
    'min_cycles', 'min_cycles_addr',
    'cycles_same_reg'
]


class Parser:
    def __init__(self, xml, config):
        self.xml = xml
        self.config = config


    # Parse measurement data from xml ans fills args dict
    def _parse_measurements(self, args, arch_node) -> bool:
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


    # Returns dict { instr_type -> list(Instructions) }
    def parse(self) -> defaultdict:
        root = ET.parse(self.xml)
        icodes = {}

        for instr_node in root.iter('instruction'):
            extension = instr_node.attrib['extension']
            if not self.config.check_extension(extension):
                continue

            # Args for the current instruction
            args = {}
            args['name'] = instr_node.attrib.get('string')
            args['iform'] = instr_node.attrib.get('iform')
            args['extension'] = extension

            ok = False

            # Gets data from specified architecture
            for arch_node in instr_node.iter('architecture'):
                if arch_node.attrib.get('name', '-') == self.config.arch:
                    ok = ok or self._parse_measurements(args, arch_node)

            if not ok:
                continue

            if math.isnan(args['min_lat']):
                continue

            args['icode'] = self.config.icode_mapping[args['name']]

            if args['icode'] in icodes:
                continue
            icodes[args['icode']] = 1

            instr = Instruction(args, self.config.ports)
            self.config.add_instruction(instr)

        return self.config.instr_groups
