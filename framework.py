import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Callable, Generator
from collections import defaultdict


def raise_() -> None:
    raise RuntimeError


class AbstractPhyExp(ABC):
    TARGET_DIR: str = 'target'
    DATA_NAME: str = 'data.json'
    INFO_KEY: str = 'INFO'
    DATA_FLOAT: list = []
    DATA_LIST: list = []

    def __init__(self) -> None:
        # 注意：为了让Streamlit能运行，这里稍微改了一下获取路径的方式
        import sys, os
        self.path = os.getcwd()
        self.data_pool = {}

    @abstractmethod
    def build_empty_data_json(self) -> None:
        pass

    def load_data(self) -> bool:
        if not self.get_target_path().exists():
            self.get_target_path().mkdir()
        if not self.get_data_path().exists():
            self.build_empty_data_json()
            # print(f'created data json at: {str(self.get_data_path())}')
            return False
        with open(str(self.get_data_path()), 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.clean_info_in_dicts(data)
        self.check_data(data)
        self.push_data_to_pool(data)
        return True

    def get_data_path(self) -> Path:
        return Path(self.path, self.TARGET_DIR, self.DATA_NAME)

    def get_target_path(self) -> Path:
        return Path(self.path, self.TARGET_DIR)

    def clean_info_in_dicts(self, target: dict) -> None:
        target.pop(self.INFO_KEY, None)
        for v in target.values():
            if isinstance(v, dict):
                self.clean_info_in_dicts(v)

    def check_data(self, data: dict) -> None:
        err = False
        for key_float in self.DATA_FLOAT:
            if key_float in data:
                err = self.check_float(key_float, data[key_float]) or err
        for key_list in self.DATA_LIST:
            if key_list in data:
                err = self.check_list_float(key_list, data[key_list]) or err
        if err:
            raise RuntimeError('invalid data')

    @classmethod
    def check_float(clz, father: str, target: dict) -> bool:
        err = False
        # 如果不是字典，说明已经被拍平了，或者直接就是值
        if not isinstance(target, dict):
            # 简单处理：如果是直接的值，就不需要遍历 items
            return False
        for k, v in target.items():
            try:
                target[k] = float(v)
            except Exception:
                err = True
                print(f'[ERROR] {father}.{k} is not a float')
        return err

    @classmethod
    def check_list_float(clz, father: str, target: dict) -> bool:
        err = False
        # 这里简化处理逻辑以适配直接的 list
        if isinstance(target, list):
            try:
                # 原地修改 list 内容
                for i in range(len(target)):
                    target[i] = float(target[i])
                return False
            except:
                print(f'[ERROR] {father} contains non-float')
                return True
        return err

    def push_data_to_pool(self, target: dict) -> None:
        for k, v in target.items():
            if isinstance(v, dict):
                self.push_data_to_pool(v)
                continue
            self.data_pool[k] = v

    def get_data_from_pool(self, target: str, default: Callable = raise_) -> object:
        if not target in self.data_pool:
            print(f'[WARN ] data not found: {target}')
            return default()
        return self.data_pool.get(target)


class DependDecoratorPool():
    def __init__(self):
        self.registry = {}
        self.dependencies = defaultdict(list)
        self.executed = set()

    def depends(self, *prereqs: Callable) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.register(func, *prereqs)
            return DependDecorator(self, func)

        return decorator

    def register(self, func: Callable, *prereqs: Callable) -> None:
        if not func.__name__ in self.registry:
            self.registry[func.__name__] = func
        for prereq in prereqs:
            self.register(prereq)
            self.dependencies[func.__name__].append(prereq.__name__)

    def run(self, func_name: str, instance: AbstractPhyExp, once: bool, *args: object) -> object:
        # 每次运行前，如果不清理 executed，第二次点按钮就不会运行了
        # 这里简单 hack 一下，实际工程中应该把 executed 放在 instance 里
        if not once:
            self.executed.clear()

        if once and func_name in self.executed:
            return
        for pre in self.dependencies[func_name]:
            self.run(pre, instance, True)
        self.executed.add(func_name)
        return self.registry[func_name](instance)


class DependDecorator():
    def __init__(self, pool: DependDecoratorPool, func: Callable):
        self.pool = pool
        self.func = func
        self.__name__ = func.__name__

    def __call(self, instance: AbstractPhyExp, *args: object) -> object:
        return self.pool.run(self.func.__name__, instance, *args)

    def __get__(self, instance: AbstractPhyExp, owner) -> Callable:
        if not isinstance(instance, AbstractPhyExp):
            raise RuntimeError('DependDecorator error')
        return lambda *args: self.__call(instance, False, *args)