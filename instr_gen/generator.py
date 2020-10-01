from instr_gen.result import Result

class Generator:
    def __init__(self):
        self.result = Result()


    def generate(self, instr_groups) -> Result:
        for ig in instr_groups:
            res = ig.solve()
            self.result.merge(res)

        return self.result
