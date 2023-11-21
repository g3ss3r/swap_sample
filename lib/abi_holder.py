import os
import json


class ABIHolder:
    _instance = None

    def __new__(cls, root_path='./abi'):
        if not isinstance(cls._instance, cls):
            cls._instance = super(ABIHolder, cls).__new__(cls)
            cls._instance.dex = None
            cls._instance.common = None
            cls._instance._entries = {}
            cls._instance._load_files(root_path)
        return cls._instance

    def _load_files(self, path):
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                setattr(self, entry, ABIHolder(full_path))
            elif entry.endswith('.json'):
                with open(full_path, 'r') as f:
                    content = json.load(f)
                setattr(self, os.path.splitext(entry)[0], content)
                self._entries[os.path.splitext(entry)[0]] = content

    def get(self, key):
        return getattr(self, key, None) or self._entries.get(key)


if __name__ == "__main__":
    # Пример использования
    abi_holder = ABIHolder(root_path='./../abi')

    print(abi_holder.erc20)
    print(abi_holder.uni_factory)
