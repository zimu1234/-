import json
import sys
import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Callable, Generator
from collections import defaultdict


def raise_() -> None:
    """辅助函数：当获取数据失败且没有提供默认值时，抛出异常"""
    raise RuntimeError


# ==============================================================================
# 1. 实验抽象基类 (AbstractPhyExp)
# 作用：所有具体实验类（如单摆、磁滞回线）的父类。
# 负责：文件读写、数据校验、类型转换、数据扁平化存储。
# ==============================================================================
class AbstractPhyExp(ABC):
    # --- 配置常量 ---
    TARGET_DIR: str = 'target'  # 数据存储的文件夹名称
    DATA_NAME: str = 'data.json'  # 数据文件名
    INFO_KEY: str = 'INFO'  # 需要在清洗时忽略的元数据键名

    # --- 类型转换配置 ---
    # 子类应重写这两个列表，告诉框架哪些字段需要自动转为 float 或 list[float]
    DATA_FLOAT: list = []
    DATA_LIST: list = []

    def __init__(self) -> None:
        """初始化实验对象，确定工作路径"""
        # 获取当前工作目录 (os.getcwd)，确保在 Streamlit 或 IDE 中都能正确找到路径
        self.path = os.getcwd()
        # 数据池：用于存放扁平化后的所有实验数据 (Key-Value 形式)
        self.data_pool = {}

    @abstractmethod
    def build_empty_data_json(self) -> None:
        """
        抽象方法：子类必须实现此方法。
        当数据文件不存在时，用于生成一个包含默认值的 JSON 模板。
        """
        pass

    def load_data(self) -> bool:
        """
        核心方法：加载并处理数据。
        流程：检查文件 -> (不存在则生成) -> 读取 -> 清洗 -> 校验类型 -> 存入数据池。
        返回：True 表示加载成功，False 表示刚生成模板(无数据)。
        """
        # 1. 确保目录存在
        if not self.get_target_path().exists():
            self.get_target_path().mkdir()

        # 2. 如果数据文件不存在，调用子类方法生成模板，并返回 False
        if not self.get_data_path().exists():
            self.build_empty_data_json()
            # print(f'created data json at: {str(self.get_data_path())}')
            return False

        # 3. 读取 JSON 文件
        with open(str(self.get_data_path()), 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 4. 数据预处理
        self.clean_info_in_dicts(data)  # 删除 INFO 字段
        self.check_data(data)  # 校验并转换数据类型 (str -> float)
        self.push_data_to_pool(data)  # 扁平化存入 data_pool

        return True

    # --- 路径获取辅助方法 ---
    def get_data_path(self) -> Path:
        """获取 data.json 的完整绝对路径"""
        # 如果子类设置了特定的 DATA_NAME (如 HysteresisExp.json)，这里会动态使用
        filename = getattr(self, 'DATA_NAME', 'data.json')
        return Path(self.path, self.TARGET_DIR, filename)

    def get_target_path(self) -> Path:
        """获取存储目录的绝对路径"""
        return Path(self.path, self.TARGET_DIR)

    # --- 数据处理逻辑 ---
    def clean_info_in_dicts(self, target: dict) -> None:
        """递归删除字典中键为 INFO 的元数据"""
        target.pop(self.INFO_KEY, None)
        for v in target.values():
            if isinstance(v, dict):
                self.clean_info_in_dicts(v)

    def check_data(self, data: dict) -> None:
        """根据配置的 list 对数据进行类型强制转换和校验"""
        err = False
        # 检查单数值 (DATA_FLOAT)
        for key_float in self.DATA_FLOAT:
            if key_float in data:
                err = self.check_float(key_float, data[key_float]) or err
        # 检查列表值 (DATA_LIST)
        for key_list in self.DATA_LIST:
            if key_list in data:
                err = self.check_list_float(key_list, data[key_list]) or err

        if err:
            raise RuntimeError('数据校验失败：存在非数字格式的数据')

    @classmethod
    def check_float(clz, father: str, target: dict) -> bool:
        """尝试将值转换为 float，失败则打印错误"""
        err = False
        # 如果 target 不是字典，说明它是直接的值，无需遍历
        if not isinstance(target, dict):
            return False

        for k, v in target.items():
            try:
                target[k] = float(v)  # 原地修改字典
            except Exception:
                err = True
                print(f'[ERROR] {father}.{k} 不是有效的浮点数')
        return err

    @classmethod
    def check_list_float(clz, father: str, target: dict) -> bool:
        """尝试将列表中的每个元素转换为 float"""
        err = False
        if isinstance(target, list):
            try:
                # 原地修改列表内容
                for i in range(len(target)):
                    target[i] = float(target[i])
                return False
            except:
                print(f'[ERROR] {father} 列表中包含非数字字符')
                return True
        return err

    def push_data_to_pool(self, target: dict) -> None:
        """
        递归地将嵌套字典“拍平”放入 self.data_pool。
        例如：{"a": {"b": 1}} -> self.data_pool["b"] = 1
        """
        for k, v in target.items():
            if isinstance(v, dict):
                self.push_data_to_pool(v)
                continue
            self.data_pool[k] = v

    def get_data_from_pool(self, target: str, default: Callable = raise_) -> object:
        """安全的从数据池中获取数据，如果不存在则调用 default 回调"""
        if not target in self.data_pool:
            print(f'[WARN ] data not found: {target}')
            return default()
        return self.data_pool.get(target)


# ==============================================================================
# 2. 依赖管理池 (DependDecoratorPool)
# 作用：管理函数间的依赖关系（拓扑排序执行）。
# 实现了“想执行B必须先自动执行A”的逻辑。
# ==============================================================================
class DependDecoratorPool():
    def __init__(self):
        self.registry = {}  # 注册表：存储函数名 -> 函数对象
        self.dependencies = defaultdict(list)  # 依赖图：存储函数名 -> [依赖1, 依赖2]
        self.executed = set()  # 记录已执行的函数，防止重复执行

    def depends(self, *prereqs: Callable) -> Callable:
        """
        装饰器工厂。
        用法：@pool.depends(func_a, func_b)
        表示被装饰的函数依赖于 func_a 和 func_b。
        """

        def decorator(func: Callable) -> Callable:
            self.register(func, *prereqs)
            return DependDecorator(self, func)

        return decorator

    def register(self, func: Callable, *prereqs: Callable) -> None:
        """注册函数及其依赖关系到池中"""
        if not func.__name__ in self.registry:
            self.registry[func.__name__] = func
        for prereq in prereqs:
            self.register(prereq)  # 递归注册前置依赖
            self.dependencies[func.__name__].append(prereq.__name__)

    def run(self, func_name: str, instance: AbstractPhyExp, once: bool, *args: object) -> object:
        """
        核心调度方法：递归执行依赖树。
        instance: 实验类的实例 (即 self)
        once: True 表示在递归内部调用，False 表示是外部触发的初始调用
        """
        # 如果是外部触发（例如点击按钮），清空已执行记录，确保能重新运行
        if not once:
            self.executed.clear()

        # 如果当前任务已执行过，则跳过（防止菱形依赖导致的重复计算）
        if once and func_name in self.executed:
            return

        # 1. 先递归执行所有前置依赖
        for pre in self.dependencies[func_name]:
            self.run(pre, instance, True)

        # 2. 标记当前任务为已执行
        self.executed.add(func_name)

        # 3. 执行当前任务，并将实验实例 (instance) 传给它
        return self.registry[func_name](instance)


# ==============================================================================
# 3. 依赖装饰器包装类 (DependDecorator)
# 作用：拦截对方法的调用，转交给 Pool 进行调度。
# 实现了描述符协议 (__get__) 以便绑定实例方法。
# ==============================================================================
class DependDecorator():
    def __init__(self, pool: DependDecoratorPool, func: Callable):
        self.pool = pool
        self.func = func
        self.__name__ = func.__name__

    def __call(self, instance: AbstractPhyExp, *args: object) -> object:
        """内部调用：触发 Pool 的 run 方法"""
        return self.pool.run(self.func.__name__, instance, *args)

    def __get__(self, instance: AbstractPhyExp, owner) -> Callable:
        """
        描述符协议：
        当在类实例上调用被装饰的方法时，此方法被触发。
        它捕获实验类的实例 `instance` (即 self)，并将其传递给 Pool。
        """
        if not isinstance(instance, AbstractPhyExp):
            raise RuntimeError('DependDecorator error: 只能用于 AbstractPhyExp 的子类')

        # 返回一个 lambda，当用户调用方法时，实际上执行的是这个 lambda
        # 这里的 False 参数告诉 Pool：这是一次新的外部调用，需要重置 executed 状态
        return lambda *args: self.__call(instance, False, *args)
