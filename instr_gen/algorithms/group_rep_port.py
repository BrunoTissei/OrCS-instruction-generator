import os
import numpy as np
import pandas as pd

from itertools import accumulate
from collections import defaultdict

from instr_gen.instruction import Instruction
from instr_gen.result import Result, ResInstruction, ResUop
from instr_gen.algorithms.algorithm import Algorithm, AlgConfig


class GroupRepPort(Algorithm):
    def __init__(self, config: AlgConfig):
        super().__init__(config)

        self.result = Result()
        self.instr_dict = self.InstrDict(config)


    def solve(self, instructions: list) -> Result:
        self._setup_counts()
        self._setup_instructions(instructions)


        solver = self.Solver(self.instr_dict)
        ans = solver.solve(self.config.params['num_uops'])

        for uop in self.instr_dict.uops:
            self.result.uops.append(uop)

        """
        for i in ans.keys():
            print(f'{i}:')
            print(f'\tnew   -> {ans[i]}')
            print(f'\torig  -> {solver.vec[i]}')
        """

        return self.result


    def _setup_counts(self) -> None:
        path = str(self.config.params['counts_path'])

        directory = os.fsdecode(path)
        self.cnt_per_icode = defaultdict(lambda: 0)

        for f in os.listdir(directory):
            filename = os.fsencode(f).decode("utf-8")
            bench_csv = pd.read_csv(path + '/' + filename)

            for i in bench_csv.iterrows():
                self.cnt_per_icode[i[1]['icode']] += i[1]['count']


    def _get_rep_port(self, ports: dict) -> str:
        rep = max(ports, key = ports.get)
        if ports[rep] > 0:
            return rep

        return None


    # Returns core latency and representative port
    def _get_instr_data(self, instr: Instruction) -> (int, int):
        lat = instr.max_lat
        ports = instr.ports

        for i in self.config.params['latency_fix']:
            if ports[i['port']] > 0:
                lat -= i['lat']
                ports[i['port']] = 0

                for j in i.get('operands', []):
                    if j['name'] in instr.operands:
                        lat -= j['lat']

        return max(lat, 1), self._get_rep_port(ports)


    def _setup_instructions(self, instructions: list) -> None:
        for instr in instructions:
            res_instr = ResInstruction(instr.icode)
            self.result.add_instruction(res_instr)

            lat, rep = self._get_instr_data(instr)
            if rep != None:
                cnt = self.cnt_per_icode[instr.icode]

                # Add res_instr to instr_dict, to be set when solved
                self.instr_dict.add_instruction(res_instr, cnt, lat, rep)



    # Set of instructions is divided by representative port (subsets)
    class InstrSet:
        def __init__(self, rep_port):
            self.num = 0
            self.counter = 0
            self.rep_port = rep_port

            self.instr_per_lat = defaultdict(lambda: [])
            self.count_per_lat = defaultdict(lambda: 0)

            self.new_uops = {}


        def add_instruction(self,
                            instr: ResInstruction,
                            count: int,
                            lat: int) -> None:
            self.num += 1
            self.instr_per_lat[lat].append(instr)
            self.count_per_lat[lat] += count


        def set_uop(self,
                    old_lat: int,
                    new_lat: int,
                    config: AlgConfig) -> ResUop:
            if new_lat not in self.new_uops:
                self.new_uops[new_lat] = (
                    config.port_to_uop[self.rep_port],
                    self.counter
                )

                self.counter += 1

            val = self.new_uops[new_lat]
            N = len(config.uop_to_fu[val[0]])

            uop_name = val[0] + '_' + str(val[1])
            uop_name = config.instruction_type + '_' + uop_name

            for i, instr in enumerate(self.instr_per_lat[old_lat]):
                instr.add_uop(uop_name)

            return ResUop(uop_name, new_lat, config.uop_to_fu[val[0]][val[1] % N])


        @property
        def vec_data(self) -> list:
            return sorted(list(self.count_per_lat.keys()))


        @property
        def cnt_data(self) -> list:
            vec = self.vec_data
            return list(map(lambda x: max(1, self.count_per_lat[x]), vec))



    # Set of all instructions of a particular type
    class InstrDict:
        def __init__(self, config: AlgConfig):
            self.config = config

            self._set = {}
            self.uops = []
            self.ports = []


        def add_instruction(self,
                            instr: ResInstruction,
                            count: int,
                            lat: int,
                            rep: str) -> None:
            if rep not in self._set:
                self.ports.append(rep)
                self._set[rep] = GroupRepPort.InstrSet(rep)

            self._set[rep].add_instruction(instr, count, lat)


        def get_data(self) -> (dict, dict):
            vec = dict([ (k, v.vec_data) for k, v in self._set.items() ])
            cnt = dict([ (k, v.cnt_data) for k, v in self._set.items() ])
            return vec, cnt


        def set_uop(self,
                    ii: int,
                    old_lat: int,
                    new_lat: int) -> None:
            uop = self._set[self.ports[ii]].set_uop(old_lat, new_lat, self.config)
            self.uops.append(uop)



    # Solver helper class
    class Solver:
        def __init__(self, instr_dict: "InstrDict"):
            self.instr_dict = instr_dict
            self.vec, self.cnt = self.instr_dict.get_data()

            self.N = len(instr_dict.ports)

            self.ans = dict([
                (k, [0] * len(v)) for k, v in self.vec.items()
            ])

            self.mult = dict([
                (k, self._dot_product(self.cnt[k], self.vec[k]))
                for k in self.cnt.keys()
            ])

            self.acc_cnts = dict([
                (k, self._prefix_sum(v))
                for k, v in self.cnt.items()
            ])

            self.acc_mult = dict([
                (k, self._prefix_sum(v))
                for k, v in self.mult.items()
            ])

            self.dp = np.zeros((200, 200, 40), dtype = int)
            self.res = np.zeros((200, 200, 40, 2), dtype = int)

            self.dp.fill(-1)


        def _prefix_sum(self, v: list) -> list:
            return list(accumulate(v))


        def _dot_product(self, v: list, u: list) -> list:
            return [ i * j for i, j in zip(v, u) ]


        # Cost function
        def C(self, l: int, r: int, ii: int) -> int:
            pid = self.pid(ii)
            if l == 0:
                return self.vec[pid][l] * self.acc_cnts[pid][r]

            bot = (self.acc_cnts[pid][r] - self.acc_cnts[pid][l - 1])
            return self.vec[pid][l] * bot


        # Weighted average of vec using cnt as weights
        def _weighted_avg(self, l: int, r: int, ii: int) -> int:
            pid = self.pid(ii)
            if l == r:
                return self.vec[pid][l]

            if l == 0:
                return self.acc_mult[pid][r] // self.acc_cnts[pid][r]

            top = (self.acc_mult[pid][r] - self.acc_mult[pid][l - 1])
            return top // (self.acc_cnts[pid][r] - self.acc_cnts[pid][l - 1])


        # Returns result of optimization
        def solve(self, K: int) -> dict:
            self._solve(0, K, 0)
            self._retrieve(0, K, 0)

            return self.ans


        # Returns port string given integer id
        def pid(self, ii: int) -> str:
            return self.instr_dict.ports[ii]


        # Solves problem recursively
        def _solve(self, i: int, k: int, ii: int) -> int:
            inf = 10**18
            if ii == self.N:
                if k != -1:
                    return -inf
                return 0

            if k <= -1:
                return -inf

            # Dynamic programming (memoization)
            if self.dp[i, k, ii] != -1:
                return self.dp[i, k, ii]

            mn = -inf
            M = len(self.vec[self.pid(ii)])

            for j in range(i, M):
                next_i  = (j + 1) % M
                next_ii = ii if (j + 1 < M) else ii + 1

                x = self._solve(next_i, k - 1, next_ii) + self.C(i, j, ii)

                if x > mn:
                    mn = x
                    self.res[i, k, ii, 0] = next_i
                    self.res[i, k, ii, 1] = next_ii

            self.dp[i, k, ii] = mn
            return self.dp[i, k, ii]


        def _retrieve(self, i: int, k: int, ii: int) -> None:
            if ii == self.N:
                return

            pid = self.pid(ii)
            if self.res[i, k, ii, 0] == 0:
                lim = len(self.vec[pid])
            else:
                lim = self.res[i, k, ii, 0]

            # x = self.vec[pid][i]
            x = self._weighted_avg(i, lim - 1, ii)

            for j in range(i, lim):
                self.instr_dict.set_uop(ii, self.vec[pid][j], x)
                self.ans[pid][j] = x

            self._retrieve(self.res[i, k, ii, 0], k - 1, self.res[i, k, ii, 1])
