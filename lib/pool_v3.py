from web3 import Web3
import requests
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
from erc20_token import ERC20Token
from abi_holder import ABIHolder


class PoolV3:
    def __init__(self, _w3, _pool_address, engine='uni'):
        self.abi_holder = ABIHolder(root_path='./abi')
        
        self.w3 = _w3
        self.address = _pool_address
        self.engine = engine

        _abi_name = str(self.engine).lower() + "_pool"
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(_pool_address),
            abi=self.abi_holder.get(_abi_name)
        )

        # переделать на мультикол
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.contract.functions.fee().call),
                executor.submit(self.contract.functions.token0().call),
                executor.submit(self.contract.functions.token1().call)
            ]
            self.fee, self.token0_address, self.token1_address = [future.result() for future in futures]

        # Calculating K for pool price
        self.token0 = ERC20Token(self.w3, self.token0_address)
        self.token1 = ERC20Token(self.w3, self.token1_address)
        self.k = self.token0.decimals - self.token1.decimals

    def encode_address(self, zto=True):
        pool_int = Web3.to_int(hexstr=self.address)
        if not zto:
            pool_int = pool_int | (1 << 255)
        return pool_int

    def usd_liquidity(self, chain_name='ethereum'):
        api_key = os.environ.get('DATALAYER_KEY')

        # TODO: вынести как отдельный датапровайдер
        url = f'https://datalayer.decommas.net/datalayer/api/v1/tokens/{self.address}?networks={chain_name}&verified=false&api-key={api_key}'

        result = requests.get(url)
        data = result.json()

        if data.get('status') != 200:
            return -1

        total_usd_value = 0.0
        for token in data['result']:
            # Преобразовать значение amount с учетом decimals
            adjusted_amount = float(token['amount']) / (10 ** token['decimals'])

            # Проверить наличие actual_price и что оно не равно None
            if token['actual_price'] and token['actual_price'] != 'null':
                usd_value = adjusted_amount * float(token['actual_price'])
                total_usd_value += usd_value

        return total_usd_value

    def get_price(self, zto=True):
        try:
            slot0 = self.contract.functions.slot0().call()
            sqrtPriceX96 = slot0[0]
            price_pool = (sqrtPriceX96 ** 2) / (2 ** 192)

            if zto:
                return float(price_pool * (10 ** self.k))
            else:
                return 1 / float(price_pool * (10 ** self.k))

        except Exception as e:
            print(e)
            return -1

    def get_amount_out(self, _amount, zto=True):
        amount = float(_amount) * self.get_price(zto)
        fee_percentage = self.fee / (10 ** 4)
       
        return float(amount) * (1 - fee_percentage)

    def health_check(self, chain='ethereum'):
        token0_balance = self.token0.get_balance(self.address)
        token1_balance = self.token1.get_balance(self.address)

        token0_value = token0_balance[1] * self.token0.get_price(chain)
        token1_value = token1_balance[1] * self.token1.get_price(chain)

        liquidity = self.usd_liquidity(chain)
        return {
            'token0_balance':   token0_balance[1],
            'token0_usd_value': token0_value,
            'token1_balance':   token1_balance[1],
            'token1_usd_value': token1_value,
            'liquidity':        liquidity
        }


# Пример использования класса
if __name__ == "__main__":
    load_dotenv(dotenv_path="./../.env")

    chain_name = "polygon"
    w3 = Web3(Web3.HTTPProvider('https://polygon.llamarpc.com'))
    pool_address = '0x1aae2bedfedb0bb1c07f599445fbb740033035fa'

    pool = PoolV3(w3, pool_address)
    print(f"Pool address: {pool.address}")
    print(f"Pool fee: {pool.fee}")
    print(f"Token0 address: {pool.token0_address} [{pool.token0.symbol}]")
    print(f"Token1 address: {pool.token1_address} [{pool.token1.symbol}]")

    encoded_address = pool.encode_address()
    print(f"Encoded pool address: {encoded_address}")

    encoded_reverse_address = pool.encode_address(zto=True)
    print(f"Encoded reverse pool address: {encoded_reverse_address}")

    # вызов пустых методов
    usd_liquidity = pool.usd_liquidity(chain_name)
    print(f"usd_liquidity: ${round(usd_liquidity, 2)}")

    pool_price = pool.get_price()
    print(f"pool_price = {pool_price}")

    print(f"K = {pool.k}")

    print(f"get_amount_out (▶) = {pool.get_amount_out(100)}")
    print(f"get_amount_out (◀)= {pool.get_amount_out(100, zto=False)}")

    print(pool.health_check(chain_name))


