def load_value(x): return normalize(x)
def normalize(x): return x.strip().lower()
class Service:
    def run(self,value): return load_value(value)
