import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        self.new_block(previous_hash = '1', proof = 100)               # Genesis Block


    def register_node(self, address):                                 # Adding new node to the list
        parsed_url = urlparse(address)                                 # Param : address of ndoe

        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL !!!')
        

    def valid_chain(self, chain):                                      # Checking validity of blockchain
        last_block = chain[0]                                          # Param : blockchain ; Return : T/F
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n**************************************\n")

            last_block_hash = self.hash(last_block)                    # Check the validity of the hash of block

            if block['previous_hash'] != last_block_hash:
                return False
            
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False
            
            last_block = block
            current_index += 1

        return True
    

    def resolve_conflicts(self):                                       # Consensus Algorithm
        neighbours = self.nodes                                        # Return : True if chain replaced
        new_chian = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False 

    def new_block(self, proof, previous_hash):                         # Creation of New Block
        block = {                                                      # Param : proof, prev hash ; Return : New Block
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.chain[-1]),
        }

        self.current_transactions = []

        self.chain.append(block)
        return block
           
        
    def new_transactions(self, sender, recipient, amount):             # Creation of New Transac
        self.current_transactions.append({                             # Param : sender, recp, amt ; Return : index of the block holding the transac
            'sender' : sender,
            'recipient' : recipient,
            'amount' : amount,
        })

        return self.last_block['index'] + 1
    
    @property

    def last_block(self):
        return self.chain[-1]
    
    @staticmethod

    def hash(block):                                                   # SHA-256 of block
        block_string = json.dumps(block, sort_keys=True).encode()      # Param : block
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self, last_block):                               # Proof of Work Algo
        last_proof = last_block['proof']                               # Param : last block ; Return : answer
        last_hash = self.hash(last_block)

        proof = 0

        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof
    
    @staticmethod

    def valid_proof(last_proof, proof, last_hash):                     # Checking Validity of the proof 
        guess = f'{last_proof}{proof}{last_hash}'.encode()             # Param : prev proof, current proof, prev block hash ; Return : T/F
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"                                # Main Condition for Valid Proof (last 4 digits are 0s)
    

# Instantiate the node
app = Flask(__name__)

# Generate globally unique address for the node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods = ['GET'])

def mine():
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    blockchain.new_transactions(
        sender="0",                                      # sender 0 => block generated via mining
        recipient=node_identifier,
        amount=1,
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message' : "New Block has been forged !!!",
        'index' : block['index'],
        'transactions' : block['transactions'],
        'proof' : block['proof'],
        'previous_hash' : block['previous_hash'],
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods = ['POST'])

def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']

    if not all(k in values for k in required):
        return 'Missing values', 400
    
    index = blockchain.new_transactions(values['sender'], values['recipient'], values['amount'])

    response = {'message' : f'Transaction has been added to the Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods = ['GET'])

def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods = ['POST'])

def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Kindly supply a valid list of nodes", 400
    
    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message' : 'New nodes have been added !!!',
        'total_nodes' : list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods = ['GET'])

def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message' : 'Our chain was replaced',
            'new_chain' : blockchain.chain,
        }

    else:
        response = {
            'message' : 'Our chain stands authoritative',
            'chain' : blockchain.chain,
        }

    return jsonify(response), 200

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type = int, help = 'port to listen on')
    args = parser.parse_args()
    port = args.port 

    app.run(host = '0.0.0.0', port = port)