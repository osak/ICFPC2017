import socket
import json
import sys
import argparse
import subprocess
from subprocess import Popen, PIPE

HOST = "punter.inf.ed.ac.uk"
verbose = False

class GameClient():
    def __init__(self, host, port, name):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        self.name = name
        self.buffer = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def handshake(self):
        self.send_object({"me": self.name})
        return self.recv_object()

    def send_object(self, obj):
        self.send_message(json.dumps(obj))

    def recv_object(self):
        return json.loads(self.recv_message())

    def send_message(self, message):
        header = "{0}:".format(len(message))
        self.client.send(header.encode("utf-8"))
        self.client.send(message.encode("utf-8"))
        if verbose:
            print("[SENT] {0}".format(message), file = sys.stderr)
    
    def recv_message(self):
        while True:
            colon_index = self.buffer.find(":")
            if colon_index != -1:
                msg_length = int(self.buffer[:colon_index])
                if len(self.buffer) - colon_index - 1 >= msg_length:
                    result = self.buffer[colon_index + 1:colon_index + 1 + msg_length]
                    self.buffer = self.buffer[colon_index + 1 + msg_length:]
                    if verbose:
                        print("[RCVD] {0}".format(result), file = sys.stderr)
                    return result
            msg = self.client.recv(4096)
            self.buffer += msg.decode("utf-8")

def encode_json(obj):
    string = json.dumps(obj)
    string_with_header = "{0}:{1}".format(len(string), string)
    if verbose:
        print("RAW INPUT: {0}".format(string_with_header), file = sys.stderr)
    return string_with_header.encode("utf-8")
    
def decode_json(bytes):
    string = bytes.decode("utf-8")
    if verbose:
        print("RAW OUTPUT: {0}".format(string), file = sys.stderr)
    colon_index = string.find(":")
    return json.loads(string[colon_index + 1:])

def execute_command(command, obj):
    command = ["bin/sandstar.rb"] + command
    process = Popen(command, stdout=PIPE, stdin=PIPE)
    buffer = ""
    colon_index = -1
    while True:
        buffer = buffer + process.stdout.read(1).decode("utf-8")
        colon_index = buffer.find(":")
        if colon_index != -1:
            msg_length = int(buffer[:colon_index])
            if len(buffer) - colon_index - 1 == msg_length:
                break
    handshake = json.loads(buffer[colon_index + 1:])
    return process.communicate(input=encode_json({"you": handshake["me"]}) + encode_json(obj))[0]

def hit_command(command, obj):
    command = ["bin/sandstar.rb"] + command
    process = Popen(command, stdout=PIPE, stdin=PIPE)
    buffer = ""
    colon_index = -1
    while True:
        buffer = buffer + process.stdout.read(1).decode("utf-8")
        colon_index = buffer.find(":")
        if colon_index != -1:
            msg_length = int(buffer[:colon_index])
            if len(buffer) - colon_index - 1 == msg_length:
                break
    handshake = json.loads(buffer[colon_index + 1:])
    process.stdin.write(encode_json({"you": handshake["me"]}) + encode_json(obj))

def aggregate_moves(moves):
    result = {}
    for move in moves:
        if "pass" in move:
            p = move["pass"]["punter"]
        else:
            p = move["claim"]["punter"]
        result[p] = move
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Talk to online server")
    parser.add_argument("port", help="Port Number", type=int)
    parser.add_argument("name", help="Name of the AI", type=str)
    parser.add_argument("command", help="Command to execute", nargs='+')
    parser.add_argument("-v", "--verbose", help="Output vervose log", action="store_true")
    parser.add_argument("-o", "--output", help="Output path of replay file", type=str, default="replay.json")
    args = parser.parse_args()
    command = args.command
    verbose = args.verbose
    output_path = args.output

    print("Port: {0}, Name: {1}".format(args.port, args.name), file = sys.stderr)
    print("Command: {0}".format(" ".join(command)), file = sys.stderr)

    log = {"history": []}
    
    with GameClient(HOST, args.port, args.name) as client:
        # Handshake
        print("Handshaking...", file = sys.stderr)
        client.handshake()
        print("Handshaking complete", file = sys.stderr)
        # Set up
        setup_input = client.recv_object()
        map = setup_input["map"]
        punter = setup_input["punter"]
        num_punter = setup_input["punters"]
        log["numPunter"] = num_punter
        log["map"] = map
        if "settings" in setup_input:
            settings = setup_input
        else:
            settings = {}
        log["settings"] = settings

        print("Setting up...", file = sys.stderr)
        print("Punter: {0}, #Punters".format(punter, num_punter), file = sys.stderr)
        print("#Vertices: {0}, #Edges: {1}, #Mines: {2}".format(len(map["sites"]), len(map["rivers"]), len(map["mines"])), file = sys.stderr)
        print("Settings: {0}".format(settings), file = sys.stderr)

        setup_output = decode_json(execute_command(command, setup_input))
        futures = [[]] * num_punter
        if "futures" in setup_output and "futures" in settings and settings["futures"]:
            myfutures = setup_output["futures"]
            futures[punter] = myfutures
        log["futures"] = futures
        state = setup_output["state"]
        del setup_output["state"]
        client.send_object(setup_output)
        print("AI ready", file = sys.stderr)

        is_first_turn = True
        # Game play
        while True:
            obj = client.recv_object()
            if "stop" in obj:
                # Clean up
                hit_command(command, obj)
                if not is_first_turn:
                    for i in range(punter, num_punter):
                        log["history"].append({"move": moves[i], "score": -1})
                for i in range(0, punter):
                    log["history"].append({"move": moves[i], "score": -1})
                log["history"] = log["history"][:len(map["rivers"])]
                print("Game finished!", file = sys.stderr)
                print(obj["stop"]["scores"], file = sys.stderr)
                log["scores"] = obj["stop"]["scores"]
                break
            if "timeout" in obj:
                continue
            obj["state"] = state
            result = decode_json(execute_command(command, obj))
            state = result["state"]
            del result["state"]
            if "claim" in result:
                print("Move: ({0}, {1})".format(result["claim"]["source"], result["claim"]["target"]), file = sys.stderr)
            elif "pass" in result:
                print("Move: Pass", file = sys.stderr)
            client.send_object(result)
            moves = aggregate_moves(obj["move"]["moves"])
            if not is_first_turn:
                for i in range(punter, num_punter):
                    log["history"].append({"move": moves[i], "score": -1})
            for i in range(0, punter):
                log["history"].append({"move": moves[i], "score": -1})

            is_first_turn = False
        print(json.dumps(log), file = open(output_path, "w"))
