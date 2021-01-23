import argparse

from instr_gen.config import Config
from instr_gen.parser import parse
from instr_gen.result import Result


# Returns parser args
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Generate instructions for OrCS'
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

    parser.add_argument('--name',
        type = str,
        action = 'store',
        default = '',
        required = True,
        help = 'Prefix of resulting files'
    )

    return parser.parse_args()


# Gets result from all instruction groups
def solve_all(instr_groups) -> Result:
    result = Result()

    for ig in instr_groups:
        tmp = ig.solve()
        result.merge(tmp)

    return result


#####################
def main() -> int:
    args = parse_args()

    print('Parsing config file')
    config = Config(args.config, args.icode)

    print('Parsing instructions xml')
    instr_groups = parse(args.xml, config)

    print('Generating results')
    result = solve_all(instr_groups)

    print('Creating files')
    result.output(args.name)
    config.output_functional_units(args.name)

    return 0
