# Resulting instruction
class ResInstruction:
    def __init__(self, icode: str):
        self.uops = []
        self.icode = icode


    def add_uop(self, uop: str) -> None:
        self.uops.append(uop)


    def __str__(self):
        uops = list(map(lambda x: f'"{x}"', self.uops))
        uops = ', '.join(uops)

        return (f'NAME = "{self.icode}"; '
                f'UOPS = [{uops}]')



# Resulting uop
class ResUop:
    def __init__(self, name: str, lat: int, fu: str, ports: str):
        self.name = name
        self.latency = lat
        self.functional_unit = fu
        self.ports = ports


    def __str__(self):
        return (f'NAME = "{self.name}"; '
                f'LATENCY = {self.latency}; '
                f'FU = "{self.functional_unit}"; '
                f'PORTS = "{self.ports}";')



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


    def output(self, name: str) -> None:
        self.uops.sort(key = lambda x: x.name)
        self.instructions.sort(key = lambda x: x.icode)

        # Output instructions
        with open(name + '_instructions.cfg', 'w+') as f:
            lines = [ f'\t{{ {str(i)} }}' for i in self.instructions ]

            print('INSTRUCTIONS = (', file = f)
            print(',\n'.join(lines), file = f)
            print(');', file = f)

        # Output uops
        with open(name + '_uops.cfg', 'w+') as f:
            lines = [ f'\t{{ {str(i)} }}' for i in self.uops ]

            print('UOPS = (', file = f)
            print(',\n'.join(lines), file = f)
            print(');', file = f)
