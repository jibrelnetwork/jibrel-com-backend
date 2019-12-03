import random


def generate_deposit_reference_code():
    alphabet = list(range(0, 9))
    code_length = 9
    code = ''.join([
        str(random.choice(alphabet)) for x in range(code_length)
    ])
    return "DEPOSIT-{}-{}-{}".format(code[:3], code[3:6], code[6:])
