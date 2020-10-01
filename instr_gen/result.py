
# Resulting instruction
class ResInstruction:
    def __init__(self, icode: str):
        self.uops = []
        self.icode = icode


    def add_uop(self, uop: str) -> None:
        self.uops.append(uop)



# Resulting uop
class ResUop:
    def __init__(self, name: str, lat: int, fu: str):
        self.name = name
        self.latency = lat
        self.functional_unit = fu



class Result:
    def __init__(self):
        self.uops = []
        self.instructions = []

        self.uop_tracker = {}
        self.instr_tracker = {}


    def add_instruction(self, instr: ResInstruction) -> None:
        if instr.icode in self.instr_tracker:
            return

        self.instr_tracker[instr.icode] = 1
        self.instructions.append(instr)


    def add_uop(self, uop: ResUop) -> None:
        if uop.name in self.uop_tracker:
            return
            
        self.uop_tracker[uop.name] = 1
        self.uops.append(uop)


    def merge(self, other: "Result") -> None:
        for uop in other.uops:
            self.add_uop(uop)

        for instr in other.instructions:
            self.add_instruction(instr)


    def output(self, name):
        self.uops.sort(key = lambda x: x.name)
        self.instructions.sort(key = lambda x: x.icode)

        # Output instructions
        with open(name + '_instructions.cfg', 'w+') as f:
            print('INSTRUCTIONS = (', file = f)

            lines = []
            for instr in self.instructions:
                uops = list(map(lambda x: f'"{x}"', instr.uops))
                uops = ', '.join(uops)

                lines.append(f'\t{{ '
                    f'NAME = "{instr.icode}"; '
                    f'UOPS = [{uops}] '
                f'}}')

            print(',\n'.join(lines), file = f)
            print(');', file = f)

        # Output uops
        with open(name + '_uops.cfg', 'w+') as f:
            print('UOPS = (', file = f)

            lines = []
            for uop in self.uops:
                lines.append(f'\t{{ '
                    f'NAME = "{uop.name}"; '
                    f'LATENCY = {uop.latency}; '
                    f'FU = "{uop.functional_unit}"; '
                f'}}')

            print(',\n'.join(lines), file = f)
            print(');', file = f)
