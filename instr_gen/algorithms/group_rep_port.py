import os
import numpy as np
import pandas as pd

from itertools import accumulate
from collections import defaultdict

from instr_gen.instruction import Instruction
from instr_gen.result import Result, ResInstruction, ResUop
from instr_gen.algorithms.algorithm import Algorithm, AlgConfig


# Algorithm used for SIMD instructions
class GroupRepPort(Algorithm):
    def __init__(self, config: AlgConfig):
        super().__init__(config)

        self.result = Result()
        self.instr_dict = self.InstrDict(config)


    def solve(self, instructions: list) -> Result:
        self._setup_counts()
        self._setup_instructions(instructions)

        # The max number of uops is limited by number of distinct latency values
        num_uops = self.config.params['num_uops']

        max_num_uops = 0
        for v in self.instr_dict._set.values():
            max_num_uops += len(v.instr_per_lat)

        if num_uops > max_num_uops:
            print(f'WARNING: num_uops set to {max_num_uops}')
            num_uops = max_num_uops

        # Solve and get answer
        solver = self.Solver(self.instr_dict)
        ans = solver.solve(num_uops)

        for uop in self.instr_dict.uops:
            self.result.uops.append(uop)

        print()
        print(f'{self.config.instruction_type}:')

        for i in ans.keys():
            transf = lambda x: ' | '.join(list(map(lambda y: f'{y:10}', x)))

            result   = transf(ans[i])
            original = transf(solver.vec[i])
            diff     = transf([ o - r for r, o in zip(ans[i], solver.vec[i]) ])
            cnts     = transf(map(lambda x: int(x/100000), solver.cnt[i]))

            print(f'\t{i}:')
            print(f'\t\tcnt  -> {cnts}')
            print(f'\t\tnew  -> {result}')
            print(f'\t\torig -> {original}')
            print(f'\t\tdiff -> {diff}')

        print()

        return self.result


    # Parses benchmark files and retrieves count per instruction
    def _setup_counts(self) -> None:
        path = str(self.config.params['counts_path'])

        directory = os.fsdecode(path)
        self.cnt_per_icode = defaultdict(lambda: 0)

        for f in os.listdir(directory):
            filename = os.fsencode(f).decode("utf-8")
            bench_csv = pd.read_csv(path + '/' + filename)

            for i in bench_csv.iterrows():
                self.cnt_per_icode[i[1]['icode']] += float(i[1]['count'])


    # Returns representative port given port usage
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


    # Adds all instructions to instr_dict
    def _setup_instructions(self, instructions: list) -> None:
        for instr in instructions:
            res_instr = ResInstruction(instr.icode)
            self.result.add_instruction(res_instr)

            lat, rep = self._get_instr_data(instr)
            if rep != None:
                cnt = self.cnt_per_icode[instr.icode]

                # Add res_instr to instr_dict, to be set when solved
                self.instr_dict.add_instruction(res_instr, cnt, lat, rep)



    # Set of instructions is enumerated by representative port (subsets)
    class InstrSet:
        def __init__(self, rep_port):
            self.uop_counter = 0
            self.rep_port = rep_port

            self.instr_per_lat = defaultdict(lambda: [])
            self.count_per_lat = defaultdict(lambda: 0)

            self.new_uops = {}


        # Called by InstrDict, adds instruction to dicts based on its latency
        def add_instruction(self,
                            instr: ResInstruction,
                            count: int,
                            lat: int) -> None:
            self.instr_per_lat[lat].append(instr)
            self.count_per_lat[lat] += count


        # Returns list of new uops and adds created uops to set's instructions
        def set_uop(self,
                    old_lat: int,
                    new_lat: int,
                    config: AlgConfig) -> ResUop:

            # Keep track of uops by new_lat
            if new_lat not in self.new_uops:
                uop = config.port_to_uop[self.rep_port]
                uop_name = uop + '_' + str(self.uop_counter)
                uop_name = config.instruction_type + '_' + uop_name

                self.new_uops[new_lat] = (
                    uop_name,
                    config.uop_to_fu[uop]
                )

                self.uop_counter += 1


            uop_name, fus = self.new_uops[new_lat]

            # Add uop to instructions with latency=old_lat in this set
            for i, instr in enumerate(self.instr_per_lat[old_lat]):

                # Some uops may be related to more than one functional unit (FU)
                if len(fus) > 1:
                    target_fu = ''

                    # In this case, samples provided in config file are
                    # analysed in order to figure out which FU is the
                    # best fit for the current instruction
                    for fi, fu in enumerate(fus):
                        for samp in config.params['samples']:
                            if fu == samp['fu']:
                                for samp_instr in samp['instructions']:
                                    if samp_instr in instr.icode:
                                        target_fu = str(fi)

                    if target_fu == '':
                        target_fu = '0'

                    instr.add_uop(uop_name + '_' + target_fu)

                # Otherwise, just add the uop
                else:
                    instr.add_uop(uop_name)


            # Return one uop for each FU, uops with more than one FU are appended
            # with FUs name for disambiguation
            result = []
            for fi, fu in enumerate(fus):
                name = uop_name + '_' + str(fi) if len(fus) > 1 else uop_name
                result.append(ResUop(name, new_lat, fu, self.rep_port[1:]))

            return result


        @property
        def vec_data(self) -> list:
            return sorted(list(self.count_per_lat.keys()))


        @property
        def cnt_data(self) -> list:
            vec = self.vec_data
            return list(map(lambda x: max(1, self.count_per_lat[x]), vec))



    # Set of all instructions
    class InstrDict:
        def __init__(self, config: AlgConfig):
            self.config = config

            # _set is a dict where the key is the representative port
            # and the value is a list of instructions
            self._set = {}
            self.uops = []
            self.ports = []


        # Called by algorithm, adds instructions to the corresponding set
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


        # Lets set add uops to instructions and adds new uops to result
        def set_uop(self,
                    ii: int,
                    old_lat: int,
                    new_lat: int) -> None:

            new_uops = self._set[self.ports[ii]].set_uop(
                old_lat,
                new_lat,
                self.config
            )

            for uop in new_uops:
                self.uops.append(uop)



    # Solver helper class
    class Solver:
        def __init__(self, instr_dict: "InstrDict"):
            self.instr_dict = instr_dict
            self.vec, self.cnt = self.instr_dict.get_data()

            self.N = len(instr_dict.ports)

            # After execution, will contain grouped latency values
            self.ans = dict([ (k, [0]*len(v)) for k, v in self.vec.items() ])

            # Used by dynamic programming
            self.dp  = np.zeros((200, 200, 40),    dtype = object)
            self.res = np.zeros((200, 200, 40, 2), dtype = object)

            self.dp.fill(-1)


        # Cost function
        def C(self, l: int, r: int, ii: int) -> int:
            pid = self.pid(ii)
            new_lat = self._weighted_avg(l, r, ii)

            new, old = 0, 0
            for i in range(l, r + 1):
                new += self.cnt[pid][i] * new_lat
                old += self.cnt[pid][i] * self.vec[pid][i]

            return abs(new - old)


        # Weighted average of vec using cnt as weights
        # (can be optimized with prefix sum vectors, only if necessary)
        def _weighted_avg(self, l: int, r: int, ii: int) -> int:
            pid = self.pid(ii)

            ss, bot = 0, 0
            for i in range(l, r + 1):
                ss += self.vec[pid][i] * self.cnt[pid][i]
                bot += self.cnt[pid][i]

            return round(ss / bot)


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
            inf = 10**25
            if ii == self.N:
                if k != 0:
                    return inf
                return 0

            # Dynamic programming (memoization)
            if self.dp[i, k, ii] != -1:
                return self.dp[i, k, ii]

            mn = inf
            M = len(self.vec[self.pid(ii)])

            for j in range(i, M):
                next_i  = (j + 1) % M
                next_ii = ii if (j + 1 < M) else ii + 1

                x = self._solve(next_i, k - 1, next_ii) + self.C(i, j, ii)

                if x < mn:
                    mn = x
                    self.res[i, k, ii, 0] = next_i
                    self.res[i, k, ii, 1] = next_ii

            self.dp[i, k, ii] = mn
            return self.dp[i, k, ii]


        # Builds result recursively by checking res table
        def _retrieve(self, i: int, k: int, ii: int) -> None:
            if ii == self.N:
                return

            pid = self.pid(ii)
            if self.res[i, k, ii, 0] == 0:
                lim = len(self.vec[pid])
            else:
                lim = self.res[i, k, ii, 0]

            x = self._weighted_avg(i, lim - 1, ii)

            for j in range(i, lim):
                self.instr_dict.set_uop(ii, self.vec[pid][j], x)
                self.ans[pid][j] = x

            self._retrieve(self.res[i, k, ii, 0], k - 1, self.res[i, k, ii, 1])
