import itertools

from instr_gen.result import Result
from instr_gen.result import ResInstruction, ResUop

from instr_gen.algorithms.algorithm import Algorithm, AlgConfig


class DirectBinary(Algorithm):
    def __init__(self, config: AlgConfig):
        super().__init__(config)
        self.result = Result()


    # Translates port usage into list of uops
    def _get_uops(self, ports: dict) -> list:
        for i in self.config.params['port_fix']:
            ports[i['port']] = 0

        # ans = [ [k] * v for k, v in ports.items() if v > 0 ]
        # ans = list(itertools.chain.from_iterable(ans))
        ans = [ k for k, v in ports.items() if v > 0 ]
        return list(map(lambda x: self.config.port_to_uop[x], ans))


    def solve(self, instructions: list) -> Result:
        uop_name = lambda x: self.config.instruction_type + '_' + x

        # For every instruction, get uops based on port usage and
        # config file specifications
        for instr in instructions:
            uops = self._get_uops(instr.ports)
            res_instr = ResInstruction(instr.icode)

            if len(uops) > 0:
                for uop in uops:
                    res_instr.add_uop(uop_name(uop))

            self.result.add_instruction(res_instr)

        inv = {}
        for port, uop in self.config.port_to_uop.items():
            inv[uop] = port[1:]

        # Create uops based on config file
        for uop, lat in self.config.params['uop_latency'].items():
            res_uop = ResUop(uop_name(uop), lat, self.config.uop_to_fu[uop][0], inv[uop])
            self.result.add_uop(res_uop)

        return self.result
