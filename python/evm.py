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
from eth_hash.auto import keccak
import evm_codes

# helper functions
def mload(memory, offset, size):
    val = 0
    if len(memory) < offset + size:
        memory += ([0] * (offset + size - len(memory)))
    for i in range(size):
        val <<= 8
        val += memory[offset + i]
    return val

def mstore(memory, data, offset, size):
    if len(memory) < offset + size:
        memory += ([0] * (offset + size - len(memory)))
    for i in range(size):
        memory[offset + size - i - 1] = (data >> (i * 8)) & 0xFF
    return memory
def unsigned_to_signed(x):
    return x if x < (2 ** 255 - 1) else x - (2 ** 256)

def signed_to_unsigned(x):
    return x if x >= 0 else x + (2 ** 256)

def invalid_position(code, pc):
    for i in range(1, 33):
        if pc < i:
            break
        if code[pc - i] == evm_codes.PUSH0 + i:
            return True
    return False

def evm(code, tx, block, state):
    pc = 0
    success = True
    stack = []
    memory = []
    log = []
    storage = dict()
    ret = None
    
    while pc < len(code):
        op = code[pc]
        pc += 1

        match op:
            case evm_codes.STOP:
                break
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
            case evm_codes.SHA3:
                offset, size = stack[0], stack[1]
                val = mload(memory, offset, size)
                
                stack = [int.from_bytes(keccak(val.to_bytes(size, byteorder='big')), byteorder='big')] + stack[2:]
            case evm_codes.ADDRESS:
                stack = [int(tx['to'], 16)] + stack
            case evm_codes.BALANCE:
                addr = hex(stack[0])
                if len(addr) < 22:
                    addr = '0x' + '0'*(22 - len(addr)) + addr[2:]
                if state is None or addr not in state or 'balance' not in state[addr]:
                    stack[0] = 0
                else:
                    stack[0] = int(state[addr]['balance'], 16)
            case evm_codes.ORIGIN:
                stack = [int(tx['origin'], 16)] + stack
            case evm_codes.CALLER:
                stack = [int(tx['from'], 16)] + stack
            case evm_codes.CALLVALUE:
                stack = [int(tx['value'], 16)] + stack
            case evm_codes.CALLDATALOAD:
                pos = stack[0]
                data = tx['data']
                end = min(pos * 2 + 64, len(data))
                data = data[pos * 2:end]
                if len(data) < 64:
                    data += ("0"*(64 - len(data)))
                stack[0] = int(data, 16)
            case evm_codes.CALLDATASIZE:
                if tx is None:
                    a = 0
                else:
                    a = len(tx.get('data', '')) / 2
                stack = [a] + stack
            case evm_codes.CALLDATACOPY:
                destoffset, offset, size = stack[0], stack[1], stack[2]
                if len(memory) < destoffset + size:
                    memory += ([0] * (destoffset + size - len (memory)))
                data = tx["data"]
                for i in range(size):
                    if (offset + i + 1) * 2 <= len(data):
                        memory[destoffset + i] = int(data[(offset + i) * 2: (offset + i + 1) * 2], 16)
                    else:
                        memory[destoffset + i] = 0
                stack = stack[3:]
            case evm_codes.CODESIZE:
                stack = [len(code)] + stack
            case evm_codes.CODECOPY:
                destoffset, offset, size = stack[0], stack[1], stack[2]
                if len(memory) < destoffset + size:
                    memory += ([0] * (destoffset + size - len (memory)))
                data = code
                for i in range(size):
                    if (offset + i) <= len(data):
                        memory[destoffset + i] = int.from_bytes(data[(offset + i): (offset + i + 1)], byteorder="big")
                    else:
                        memory[destoffset + i] = 0
                stack = stack[3:]
            case evm_codes.GASPRICE:
                stack = [int(tx['gasprice'], 16)] + stack
            case evm_codes.EXTCODESIZE:
                addr = hex(stack[0])
                if len(addr) < 22:
                    addr = '0x' + '0'*(22 - len(addr)) + addr[2:]
                if state is None or addr not in state or 'code' not in state[addr]:
                    stack[0] = 0
                else:
                    stack[0] = len(state[addr]['code']['bin']) / 2
            case evm_codes.EXTCODECOPY:
                addr, destoffset, offset, size = hex(stack[0]), stack[1], stack[2], stack[3]
                if len(addr) < 22:
                    addr = '0x' + '0'*(22 - len(addr)) + addr[2:]
                if state is None or addr not in state or 'code' not in state[addr]:
                    extcode = b''
                else:
                    extcode = bytes.fromhex(state[addr]['code']['bin'])
                if len(memory) < destoffset + size:
                    memory += ([0] * (destoffset + size - len (memory)))
                data = extcode
                for i in range(size):
                    if (offset + i) <= len(data):
                        memory[destoffset + i] = int.from_bytes(data[(offset + i): (offset + i + 1)], byteorder="big")
                    else:
                        memory[destoffset + i] = 0
                stack = stack[4:]
            case evm_codes.EXTCODEHASH:
                addr = hex(stack[0])
                if len(addr) < 22:
                    addr = '0x' + '0'*(22 - len(addr)) + addr[2:]
                if state is None or addr not in state:
                    a = 0
                elif 'code' not in state[addr]:
                    a = int.from_bytes(keccak(b''), byteorder='big')
                else:
                    extcode = bytes.fromhex(state[addr]['code']['bin'])
                    a = int.from_bytes(keccak(extcode), byteorder='big')
                stack[0] = a
            case evm_codes.BLOCKHASH:
                stack = [0] + stack[1:]
            case evm_codes.COINBASE:
                stack = [int(block['coinbase'], 16)] + stack
            case evm_codes.TIMESTAMP:
                stack = [int(block['timestamp'], 16)] + stack
            case evm_codes.NUMBER:
                stack = [int(block['number'], 16)] + stack
            case evm_codes.DIFFICULTY:
                stack = [int(block['difficulty'], 16)] + stack
            case evm_codes.GASLIMIT:
                stack = [int(block['gaslimit'], 16)] + stack
            case evm_codes.CHAINID:
                stack = [int(block['chainid'], 16)] + stack
            case evm_codes.SELFBALANCE:
                addr = tx["to"]
                stack = [0] + stack
                if state is None or addr not in state or 'balance' not in state[addr]:
                    stack[0] = 0
                else:
                    stack[0] = int(state[addr]['balance'], 16)
            case evm_codes.BASEFEE:
                stack = [int(block['basefee'], 16)] + stack
            case evm_codes.POP:
                stack = stack[1:]
            case evm_codes.MLOAD:
                pos = stack[0]
                stack[0] = mload(memory, pos, 32)
            case evm_codes.MSTORE:
                pos, val = stack[0], stack[1]
                stack = stack[2:]
                if len(memory) < pos + 32:
                    memory += ([0] * (pos + 32 - len(memory)))
                for i in range(32):
                    memory[pos + 31 - i] = (val >> (i * 8)) & 0xFF
            case evm_codes.MSTORE8:
                pos, val = stack[0], stack[1] & 0xFF
                stack = stack[2:]
                if len(memory) <= pos:
                    memory += ([0] * (pos + 1 - len(memory)))
                memory[pos] = val
            case evm_codes.SLOAD:
                k = stack[0]
                stack[0] = storage.get(k, 0)
            case evm_codes.SSTORE:
                k, v = stack[0], stack[1]
                storage[k] = v
                stack = stack[2:]
            case evm_codes.JUMP:
                pc = stack[0]
                stack = stack[1:]
                if code[pc] != evm_codes.JUMPDEST or invalid_position(code, pc):
                    success = False
                    break
            case evm_codes.JUMPI:
                if stack[1] != 0:
                    pc = stack[0]
                    stack = stack[2:]
                    if code[pc] != evm_codes.JUMPDEST or invalid_position(code, pc):
                        success = False
                        break
                else:
                    stack = stack[2:]
            case evm_codes.PC:
                stack = [pc - 1] + stack
            case evm_codes.MSIZE:
                stack = [(len(memory) // 32 + int(len(memory) % 32 > 0)) * 32] + stack
            case evm_codes.GAS:
                stack = [0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff] + stack
            case evm_codes.JUMPDEST:
                continue
            case evm_codes.PUSH0:
                stack.append(0)
            case x if x in range(evm_codes.PUSH1, evm_codes.PUSH32+1):
                length = op - evm_codes.PUSH0
                b = int(code[pc:pc + length].hex(), 16)
                pc += length
                stack = [b] + stack
            case x if x in range(evm_codes.DUP1, evm_codes.DUP16+1):
                stack = [stack[x - evm_codes.DUP1]] + stack
            case x if x in range(evm_codes.SWAP1, evm_codes.SWAP16+1):
                n = x - evm_codes.SWAP1 + 1
                stack[0], stack[n] = stack[n], stack[0]
            case x if x in range(evm_codes.LOG0, evm_codes.LOG4 + 1):
                offset, size = stack[0], stack[1]
                index = x - evm_codes.LOG0
                topics = [hex(stack[2+i]) for i in range(index)]
                stack = stack[2+index:]
                data = ""
                if len(memory) < pos + 32:
                    memory += ([0] * (pos + 32 - len(memory)))
                for i in range(size):
                    data += hex(memory[offset + i])[2:]
                log.append({
                    "address": tx['to'],
                    "data": data,
                    "topics": topics
                })
            case evm_codes.CALL:
                gas, address, value, argsOffset, argsSize, retOffset, retSize = stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6]
                stack = stack[7:]
                address = hex(address)
                if len(address) < 22:
                    address = '0x' + '0'*(22 - len(address)) + address[2:]
                args = mload(memory, argsOffset, argsSize)
                new_tx = {
                    "to": address,
                    "value": value,
                    "origin": tx.get("origin") if tx else None,
                    "from": tx.get("to") if tx else None
                }
                succ, _, llog, rr = evm(bytes.fromhex(state[address]['code']['bin']), new_tx, block, state)
                rr = rr[:retSize * 2]
                log += llog
                memory = mstore(memory, int(rr, 16), retOffset, retSize)
                
                stack = [int(succ)] + stack

            case evm_codes.RETURN:
                val = hex(mload(memory, stack[0], stack[1]))[2:]
                ret = val.rjust(stack[1]*2, '0')
                stack = stack[2:]
                break
            case evm_codes.REVERT:
                val = hex(mload(memory, stack[0], stack[1]))[2:]
                ret = val.ljust(stack[1]*2, '0')
                stack = stack[2:]
                success = False
                break
            case _:
                success = False
                break

    return (success, stack, log, ret)

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
            tx = test.get('tx')
            block = test.get('block')
            state = test.get('state')
            (success, stack, log, ret) = evm(code, tx, block, state)

            expected_stack = [int(x, 16) for x in test['expect'].get('stack', [])]
            expected_log = test['expect'].get('logs', [])
            expected_return = test['expect'].get("return", None)
            
            if stack != expected_stack or success != test['expect']['success'] or expected_log != log or expected_return != ret:
                print(f"❌ Test #{i + 1}/{total} {test['name']}")
                if stack != expected_stack:
                    print("Stack doesn't match")
                    print(" expected:", expected_stack)
                    print("   actual:", stack)
                elif expected_log != log:
                    print("Log doesn't match")
                    print(" expected:", expected_log)
                    print("   actual:", log)
                elif expected_return != ret:
                    print("Return doesn't match")
                    print(" expected:", expected_return)
                    print("   actual:", ret)
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
