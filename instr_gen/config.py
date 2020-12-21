import io, libconf
from collections import defaultdict

from instr_gen.result import Result
from instr_gen.instruction import Instruction

from instr_gen.algorithms.algorithm import AlgConfig
from instr_gen.algorithms.direct_binary import DirectBinary
from instr_gen.algorithms.group_rep_port import GroupRepPort


def create_algorithm(params: AlgConfig):
    algorithms = {
        'group_rep_port': GroupRepPort,
        'direct_binary': DirectBinary
    }

    return algorithms[params.type](params)



class InstructionGroup:
    def __init__(self, config: libconf.AttrDict):
        self.name = config['name']
        self.exts = config['extensions']
        self.needs_latency = config['needs_latency']

        params = AlgConfig(config, self.name)
        self.algorithm = create_algorithm(params)
        self.instructions = []


    def add_instruction(self, instr: Instruction) -> None:
        self.instructions.append(instr)


    def solve(self) -> Result:
        self.instructions.sort(key = lambda x: x.icode)
        return self.algorithm.solve(self.instructions)



class FunctionalUnit:
    def __init__(self, config: libconf.AttrDict):
        self.name      = config['name']
        self.size      = config['size']
        self.wait_next = config['wait_next']



class Config:
    def __init__(self, cfg_path, icode_path):

        # Load config using libconf library
        with io.open(cfg_path) as f:
            config = libconf.load(f)

        # Parse icode mapping
        self.icode_mapping = {}
        self._parse_icodes(icode_path)

        # Parse architecture
        self.arch = config['arch']

        # Parse ports
        self.ports = config['ports']

        # Parse functional units
        self.functional_units = [
            FunctionalUnit(i)
            for i in config['functional_units']
        ]

        # Parse and create extension groups
        self.instr_type = {}
        self.instr_groups = []

        for cfg in config['instruction_groups']:
            instr_group = InstructionGroup(cfg)
            self.instr_groups.append(instr_group)

            for ext in instr_group.exts:
                assert(ext not in self.instr_type)
                self.instr_type[ext] = instr_group


    # Parses icode mapping libconfig file
    def _parse_icodes(self, path: str) -> None:
        with io.open(path) as f:
            data = libconf.load(f)

        for i in data['instructions']:
            self.icode_mapping[i['instr']] = i['icode']


    # Adds instruction to appropriate instruction group
    def add_instruction(self, instr: Instruction) -> None:
        ext = instr.extension
        self.instr_type[ext].add_instruction(instr)


    # Checks whether extension is specified by config file
    def check_extension(self, ext: str) -> bool:
        return ext in self.instr_type


    def needs_latency(self, ext: str) -> bool:
        return self.instr_type[ext].needs_latency


    def output_functional_units(self, name: str) -> None:
        self.functional_units.sort(key = lambda x: x.name)

        with open(name + '_functional_units.cfg', 'w+') as f:
            print('FUNCTIONAL_UNITS = (', file = f)

            lines = []
            for fu in self.functional_units:
                lines.append(f'\t{{ '
                    f'NAME = "{fu.name}"; '
                    f'SIZE = {fu.size}; '
                    f'WAIT_NEXT = {fu.wait_next}; '
                f'}}')

            print(',\n'.join(lines), file = f)
            print(');', file = f)
