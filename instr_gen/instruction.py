class Instruction:
    def __init__(self, args, all_ports):
        self.name  = args['name']
        self.icode = args['icode']
        self.extension = args['extension']

        self.min_lat = args['min_lat']
        self.max_lat = args['max_lat']

        self.num_uops = args['num_uops']

        self.operands = self._parse_operands(self.name)
        self.ports    = self._parse_ports(args['ports'], all_ports)


    # Gets operands from instructions's string
    def _parse_operands(self, name: str) -> list:
        x = name.split(' (')[-1]
        if x[-1] == ')':
            return x[:-1].split(', ')
        return []


    # Parse ports from string form to dict
    def _parse_ports(self, ports_str: str, all_ports: list) -> dict:
        ports = dict(map(lambda x: (x, 0), all_ports))

        # Convert ports from uops.info notation to dict
        if self.num_uops > 0:
            tmp = dict(map(
                lambda x: tuple(x.split('*')[::-1]),
                ports_str.split('+')
            ))

            for k, v in tmp.items():
                ports[k] += int(v)

        return ports
