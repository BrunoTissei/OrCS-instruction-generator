import abc
import libconf

from instr_gen.result import Result


class AlgConfig:
    def __init__(self, config: libconf.AttrDict, name: str):
        self.instruction_type = name

        self.params      = dict(config['algorithm'])
        self.uop_to_fu   = dict(config['uop_to_fu'])
        self.port_to_uop = dict(config['port_to_uop'])

        self.type = self.params['type']


class Algorithm(metaclass = abc.ABCMeta):
    def __init__(self, config: AlgConfig):
        self.config = config


    @abc.abstractmethod
    def solve(self, instructions: list) -> Result:
        pass
