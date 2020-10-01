import argparse

from instr_gen.config import Config
from instr_gen.parser import Parser
from instr_gen.generator import Generator


# Returns parser args
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Merge libconfig files.'
    )

    parser.add_argument('--config',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'Libconfig file'
    )

    parser.add_argument('--xml',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'instructions.xml (uops.info)'
    )

    parser.add_argument('--icode',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'icode_mapping.cfg'
    )

    return parser.parse_args()


#####################
def main() -> int:
    args = parse_args()

    print('Parsing config file')
    config = Config(args.config, args.icode)

    print('Parsing instructions xml')
    parser = Parser(args.xml, config)
    instr_groups = parser.parse()

    print('Generating results')
    generator = Generator()
    result = generator.generate(instr_groups)

    print('Creating files')
    result.output('full')
    config.output_functional_units('full')

    return 0
