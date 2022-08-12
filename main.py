'''
rinkeby testnet configs:
api url: 	https://eth-rinkeby.alchemyapi.io/v2/S-YX-8P5wBaJYmv9F13G_dZ6Z7hhnWZQ
chainId: 	4
gas: 		70000
gasPrice: 	30 gwei

'''
import os, sys
import json
import time

import traceback
from threading import Thread

from web3 import Web3, middleware
from web3.gas_strategies.time_based import fast_gas_price_strategy


class NFT_worker():
	def __init__(self, node_url):
		self.w3 = Web3(Web3.HTTPProvider(node_url))
		if self.w3.isConnected() is False:
			raise ConnectionError

		self.w3.eth.set_gas_price_strategy(fast_gas_price_strategy)
		self.w3.middleware_onion.add(middleware.time_based_cache_middleware)
		self.w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
		self.w3.middleware_onion.add(middleware.simple_cache_middleware)

	def send_trx(self, from_addr, private_key, to_addr, token_contract_addr, amount):
		self.w3.eth.account.enable_unaudited_hdwallet_features()

		with open('erc20abi.json') as file:
			abi = json.loads(file.read())

		account = self.w3.eth.account.privateKeyToAccount(private_key)
		contract = self.w3.eth.contract(address=token_contract_addr, abi=abi)
		nonce = self.w3.eth.getTransactionCount(from_addr)

		txn = contract.functions.transfer(
			to_addr,
			int(amount*(10**18)),
		)

		gas = txn.estimateGas({'from':from_addr})

		txn = txn.buildTransaction({
			'chainId': 1,
			'gas': gas,
			'gasPrice': Web3.toWei('10', 'gwei'),
			'nonce': nonce,
		})

		signed_txn = account.signTransaction(txn)
		self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)  

	def check_pool(self, pool, configs, configs_path):
		for tx_hash in pool:
			try:
				tx = self.w3.eth.getTransaction(tx_hash)
			except Exception as e:
				continue

			config = configs.get(str(tx.to).lower(), False)
			if config is False:
				continue
				
			ctrc_input = str(tx.input)

			print(f"{'-'*10}", flush=True)
			print(f'contract detected: {tx.to}', flush=True)

			if config['is_active']:
				tokenid_hex = str(hex(int(config['token_id'])))[2:]
				print("********", flush=True)
				if tokenid_hex in ctrc_input:
					print(f"token moved: {config['token_id']}", flush=True)

					self.send_trx(
						from_addr=config['send']['from_addr'],
						private_key=config['send']['private_key'],
						to_addr=config['send']['to_addr'],
						token_contract_addr=config['send']['token_contract_addr'],
						amount=config['send']['amount'] 
					)

					configs[str(tx.to).lower()]['is_active'] = False

					with open(configs_path, 'w') as file:
						json.dump(configs, file)

					print(f"{config['send']['amount']} was sent", flush=True)

			print(f"{'-'*10}", flush=True)


def split_list(alist, wanted_parts=1):
    length = len(alist)
    for i in range(wanted_parts):
    	s = alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
    	if s:
    		yield s

def main():
	# time.sleep(60)
	configs_path = '/root/nft_watch_send/configs.json'
	# worker = NFT_worker('http://127.0.0.1:8545')
	worker = NFT_worker('https://eth-rinkeby.alchemyapi.io/v2/S-YX-8P5wBaJYmv9F13G_dZ6Z7hhnWZQ')

	with open(configs_path) as file:
		configs = json.loads(file.read())

	filtr = worker.w3.eth.filter('pending')

	while True:
		try:
			pool = filtr.get_new_entries()
		except:
			filtr = worker.w3.eth.filter('pending')
			pool = filtr.get_new_entries()

		l = len(pool)

		if l:
			print(l)
			for part in split_list(pool, wanted_parts=100):
				# worker.check_pool(pool, configs, configs_path)
				Thread(target=worker.check_pool, args=(part, configs, configs_path)).start()
		else:
			pass


if __name__ == '__main__':
	main()
