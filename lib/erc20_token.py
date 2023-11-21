from web3 import Web3
from web3.middleware import geth_poa_middleware
from concurrent.futures import ThreadPoolExecutor
import os
import requests
from abi_holder import ABIHolder


class ERC20Token:
    def __init__(self, _w3, _token_address):
        self.w3 = _w3
        self.abi_holder = ABIHolder(root_path='./../abi')

        self.address = _token_address
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(_token_address), abi=self.abi_holder.erc20)

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.contract.functions.decimals().call),
                executor.submit(self.contract.functions.name().call),
                executor.submit(self.contract.functions.symbol().call),
                executor.submit(self.contract.functions.totalSupply().call)
            ]
            self.decimals, self.name, self.symbol, self.total_supply = [future.result() for future in futures]

    def get_price(self, _chain, _to='usd'):
        api_key = os.environ.get('DATALAYER_KEY')

        # TODO: вынести как отдельный датапровайдер
        _url = f"https://datalayer.decommas.net/datalayer/api/v1/token_metadata/{_chain}/{self.address}?api-key={api_key}"
        _response = requests.get(_url)
        token_data = _response.json()
        token_actual_price = token_data["result"]["actual_price"]
        return 0 if token_actual_price is None else float(token_actual_price)


    def int_by_value(self, _value):
        return int(_value * (10 ** self.decimals))

    
    def value_by_int(self, _value_int):
        return _value_int / (10 ** self.decimals)

    
    def get_balance(self, _owner):
        _balance = self.contract.functions.balanceOf(Web3.to_checksum_address(_owner)).call()
        return _balance, self.value_by_int(_balance)

    
    def allowance(self, _owner, _spender):
        _owner = Web3.to_checksum_address(_owner)
        _spender = Web3.to_checksum_address(_spender)

        _allowance = self.contract.functions.allowance(_owner, _spender).call()
        return _allowance, self.value_by_int(_allowance)

    
    def get_approve_tx(self, _owner, _spender, approve_size):
        _owner = Web3.to_checksum_address(_owner)
        _spender = Web3.to_checksum_address(_spender)
        approval_int = self.int_by_value(approve_size)
        return self.contract.functions.approve(_spender, approval_int).build_transaction({
            'from': _owner,
            'nonce': self.w3.eth.get_transaction_count(_owner)
        })


if __name__ == "__main__":
    # Используйте ваш URL-адрес провайдера и адрес токена
    w3 = Web3(Web3.HTTPProvider('https://polygon.llamarpc.com'))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    token_address = '0x2791bca1f2de4661ed88a30c99a7a9449aa84174'
    erc20 = ERC20Token(w3, token_address)

    # Примеры использования методов
    value = 123.45
    value_int = erc20.int_by_value(value)
    print(f"Человеческое количество токенов {value} равно {value_int} в целых единицах")

    value_back = erc20.value_by_int(value_int)
    print(f"Целое количество токенов {value_int} равно {value_back} в человеческом виде")

    account_address = '0x04a8f552e6d13fd00def492d243198e841a8f107'
    balance = erc20.get_balance(account_address)
    print(f"Баланс: {balance}")

    spender_address = '0x1111111254fb6c44bAC0beD2854e76F90643097d'
    allowance_value = erc20.allowance(account_address, spender_address)
    print(f"Разрешение: {allowance_value}")

    usd_price = erc20.get_price('polygon')
    print(usd_price)

    approve_tx = erc20.get_approve_tx(account_address, spender_address, 1000)
    print("Транзакция на утверждение:", approve_tx)
