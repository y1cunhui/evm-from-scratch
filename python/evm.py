#!/usr/bin/env python3

# EVM From Scratch
# Python template
#
# To work on EVM From Scratch in Python:
#
# - Install Python3: https://www.python.org/downloads/
# - Go to the `python` directory: `cd python`
# - Edit `evm.py` (this file!), see TODO below
# - Run `python3 evm.py` to run the tests

import json
import os
import evm_codes

# helper functions
def unsigned_to_signed(x):
    return x if x < (2 ** 255 - 1) else x - (2 ** 256)

def signed_to_unsigned(x):
    return x if x >= 0 else x + (2 ** 256)


def evm(code):
    pc = 0
    success = True
    stack = []
    
    while pc < len(code):
        op = code[pc]
        pc += 1

        match op:
            case evm_codes.STOP:
                break
            case evm_codes.POP:
                stack = stack[1:]
            case evm_codes.ADD:
                stack = [stack[0] + stack[1]] + stack[2:]
                if stack[0] > (2 ** 256) - 1:
                    stack[0] -= (2 ** 256)
            case evm_codes.MUL:
                stack = [stack[0] * stack[1]] + stack[2:]
                if stack[0] > (2 ** 256) - 1:
                    stack[0] %= (2 ** 256)
            case evm_codes.SUB:
                stack = [stack[0] - stack[1]] + stack[2:]
                if stack[0] < 0:
                    stack[0] += (2 ** 256)
            case evm_codes.DIV:
                if stack[1] == 0:
                    stack = [0] + stack[2:]
                else:
                    stack = [stack[0] // stack[1]] + stack[2:]
            case evm_codes.SDIV:
                if stack[1] == 0:
                    stack = [0] + stack[2:]
                else:
                    stack[0] = unsigned_to_signed(stack[0])
                    stack[1] = unsigned_to_signed(stack[1])
                    num = signed_to_unsigned(stack[0] // stack[1])
                    stack = [num] + stack[2:]
            case evm_codes.MOD:
                if stack[1] == 0:
                    stack = [0] + stack[2:]
                else:
                    stack = [stack[0] % stack[1]] + stack[2:]
            case evm_codes.SMOD:
                if stack[1] == 0:
                    stack = [0] + stack[2:]
                else:
                    stack[0] = unsigned_to_signed(stack[0])
                    stack[1] = unsigned_to_signed(stack[1])
                    num = signed_to_unsigned(stack[0] % stack[1])
                    stack = [num] + stack[2:]
            case evm_codes.ADDMOD:
                if stack[2] == 0:
                    stack = [0] + stack[3:]
                else:
                    stack = [(stack[0] + stack[1]) % stack[2]] + stack[3:]
            case evm_codes.MULMOD:
                if stack[2] == 0:
                    stack = [0] + stack[3:]
                else:
                    stack = [(stack[0] * stack[1]) % stack[2]] + stack[3:]
            case evm_codes.EXP:
                stack = [stack[0] ** stack[1]] + stack[2:]
                if stack[0] > (2 ** 256) - 1:
                    stack[0] %= (2 ** 256)
            case evm_codes.SIGNEXTEND:
                sz = stack[0]
                num = bin(stack[1] % (256 ** (sz + 1)))
                if len(num) - 2 == (sz + 1) * 8:
                    num = '0b' + '1' * (32 * 8 + 2 - len(num)) + num[2:]
                stack = [int(num, 2)] + stack[2:]
            case evm_codes.LT:
                stack = [int(stack[0] < stack[1])] + stack[2:]
            case evm_codes.GT:
                stack = [int(stack[0] > stack[1])] + stack[2:]
            case evm_codes.SLT:
                stack = [int(unsigned_to_signed(stack[0]) < unsigned_to_signed(stack[1]))] + stack[2:]
            case evm_codes.SGT:
                stack = [int(unsigned_to_signed(stack[1]) < unsigned_to_signed(stack[0]))] + stack[2:]
            case evm_codes.EQ:
                stack = [int(stack[0] == stack[1])] + stack[2:]
            case evm_codes.ISZERO:
                stack = [int(stack[0] == 0)] + stack[1:]
            case evm_codes.AND:
                stack = [stack[0] & stack[1]] + stack[2:]
            case evm_codes.OR:
                stack = [stack[0] | stack[1]] + stack[2:]
            case evm_codes.XOR:
                stack = [stack[0] ^ stack[1]] + stack[2:]
            case evm_codes.NOT:
                stack = [stack[0] ^ ((2 ** 256) - 1)] + stack[1:]
            case evm_codes.BYTE:
                if stack[0] not in range(0, 32):
                    stack = [0] + stack[2:]
                else:
                    stack = [(stack[1] >> (8*(31 - stack[0]))) & 0xFF] + stack[2:]
            case evm_codes.SHL:
                stack = [(stack[1] << stack[0]) & ((2 ** 256) - 1)] + stack[2:]
            case evm_codes.SHR:
                stack = [stack[1] >> stack[0]] + stack[2:]
            case evm_codes.SAR:
                num = bin(stack[1])
                if stack[0] >= 256:
                    num = int('0b' + '1' * 256, 2) if len(num) - 2 == 32 * 8 else 0
                elif len(num) - 2 == 32 * 8:
                    num = bin(stack[1] >> stack[0])
                    if int(num, 2) == 0:
                        num = '0b'
                    num = int('0b' + '1' * (32 * 8 + 2 - len(num)) + num[2:], 2)
                else:
                    num = stack[1] >> stack[0]
                stack = [num] + stack[2:]
            case evm_codes.PUSH0:
                stack.append(0)
            case x if x in range(evm_codes.PUSH1, evm_codes.PUSH32+1):
                length = op - evm_codes.PUSH0
                b = int(code[pc:pc + length].hex(), 16)
                pc += length
                stack = [b] + stack
            case x if x in range(evm_codes.DUP1, evm_codes.DUP32+1):
                stack = [stack[x - evm_codes.DUP1]] + stack


                
            
        

    return (success, stack)

def test():
    script_dirname = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dirname, "..", "evm.json")
    with open(json_file) as f:
        data = json.load(f)
        total = len(data)

        for i, test in enumerate(data):
            # Note: as the test cases get more complex, you'll need to modify this
            # to pass down more arguments to the evm function
            code = bytes.fromhex(test['code']['bin'])
            (success, stack) = evm(code)

            expected_stack = [int(x, 16) for x in test['expect']['stack']]
            
            if stack != expected_stack or success != test['expect']['success']:
                print(f"❌ Test #{i + 1}/{total} {test['name']}")
                if stack != expected_stack:
                    print("Stack doesn't match")
                    print(" expected:", expected_stack)
                    print("   actual:", stack)
                else:
                    print("Success doesn't match")
                    print(" expected:", test['expect']['success'])
                    print("   actual:", success)
                print("")
                print("Test code:")
                print(test['code']['asm'])
                print("")
                print("Hint:", test['hint'])
                print("")
                print(f"Progress: {i}/{len(data)}")
                print("")
                break
            else:
                print(f"✓  Test #{i + 1}/{total} {test['name']}")

if __name__ == '__main__':
    test()
