from framework import AbstractPhyExp, DependDecoratorPool
import math

# ==========================================
# 实验 1: 单摆测重力加速度
# ==========================================
pendulum_pool = DependDecoratorPool()


class PendulumExp(AbstractPhyExp):
    DATA_LIST = ['L_list', 'T_list']
    DATA_FLOAT = []

    def build_empty_data_json(self) -> None:
        pass

    @pendulum_pool.depends()
    def step1_calculate_g(self):
        l_list = self.get_data_from_pool('L_list')
        t_list = self.get_data_from_pool('T_list')
        if not l_list or not t_list: return

        g_results = []
        print(f"--- 单摆计算 (共{len(l_list)}组) ---")
        for i, (l, t) in enumerate(zip(l_list, t_list)):
            if t == 0: continue
            g = (4 * (math.pi ** 2) * l) / (t ** 2)
            g_results.append(g)
            print(f"第 {i + 1} 组: L={l}m, T={t}s => g = {g:.4f}")
        self.data_pool['g_results'] = g_results

    @pendulum_pool.depends(step1_calculate_g)
    def step2_average(self):
        results = self.get_data_from_pool('g_results')
        if results:
            avg_g = sum(results) / len(results)
            print(f"\n最终结果: g = {avg_g:.4f} m/s²\n")


# ==========================================
# 实验 2: 伏安法测电阻
# ==========================================
ohm_pool = DependDecoratorPool()


class OhmExp(AbstractPhyExp):
    DATA_FLOAT = ['U', 'I']
    DATA_LIST = []

    def build_empty_data_json(self) -> None: pass

    @ohm_pool.depends()
    def calc_R(self):
        u = self.get_data_from_pool('U')
        i = self.get_data_from_pool('I')
        if i != 0:
            print(f"U={u}V, I={i}A => R={u / i:.2f}Ω")


# ==========================================
# 实验 3: 磁滞回线 (H-B计算 & 绘图数据)
# ==========================================
hysteresis_pool = DependDecoratorPool()


class HysteresisExp(AbstractPhyExp):
    DATA_FLOAT = ["N1", "N2", "l", "S", "Sx", "Sy", "R1", "R2", "C_uf"]
    DATA_LIST = ["X_list", "Y_list"]

    def build_empty_data_json(self) -> None:
        template = {
            "N1": 100, "N2": 300, "l": 0.084, "S": 2.21e-4,
            "Sx": 0.2, "Sy": 0.2, "R1": 1.9, "R2": 1.1e3, "C_uf": 2.0,
            "X_list": ["0.5", "1.0", "1.5"], "Y_list": ["0.8", "1.6", "2.4"],
            "INFO": "默认参数"
        }
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4)

    @hysteresis_pool.depends()
    def calculate_BH(self):
        n1 = self.get_data_from_pool("N1")
        n2 = self.get_data_from_pool("N2")
        l = self.get_data_from_pool("l")
        s = self.get_data_from_pool("S")
        sx = self.get_data_from_pool("Sx")
        sy = self.get_data_from_pool("Sy")
        r1 = self.get_data_from_pool("R1")
        r2 = self.get_data_from_pool("R2")
        c = self.get_data_from_pool("C_uf") * 1e-6

        x_list = self.get_data_from_pool("X_list")
        y_list = self.get_data_from_pool("Y_list")

        if not x_list or not y_list: return

        print(f"{'No.':<4} | {'H (A/m)':<12} | {'B (T)':<12} | {'μ (H/m)':<12}")
        print("-" * 50)

        res_H, res_B, res_mu = [], [], []

        for i, (x, y) in enumerate(zip(x_list, y_list)):
            H = (n1 * x * sx) / (l * r1)
            B = (r2 * c * y * sy) / (n2 * s)
            mu = B / H if H != 0 else 0

            res_H.append(H)
            res_B.append(B)
            res_mu.append(mu)
            print(f"{i + 1:<4} | {H:<12.4f} | {B:<12.6f} | {mu:<12.6f}")

        self.data_pool["Results_H"] = res_H
        self.data_pool["Results_B"] = res_B
        self.data_pool["Results_mu"] = res_mu


# ==========================================
# 实验 4: 静电场描绘 (Electric Field) - 补回来的
# ==========================================
cufield_pool = DependDecoratorPool()


class ElectricFieldExp(AbstractPhyExp):
    # 配置：'输入Key': 理论参考值 (cm)
    SETTINGS = {
        'r(cm)7.5V': 1.38,
        'r(cm)6.0V': 1.91,
        'r(cm)4.5V': 2.63,
        'r(cm)3.0V': 3.63,
        'r(cm)1.5V': 5.05
    }
    DATA_LIST = list(SETTINGS.keys())
    DATA_FLOAT = []

    def build_empty_data_json(self) -> None:
        # 生成默认模板，每组填4个0
        template = {k: [0, 0, 0, 0] for k in self.DATA_LIST}
        template["INFO"] = "静电场实验数据"
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4)

    @cufield_pool.depends()
    def calculate_results(self):
        print(f"{'电压':<10} | {'测量均值':<10} | {'理论值':<10} | {'相对误差(%)':<10}")
        print("-" * 60)

        for key, theo_val in self.SETTINGS.items():
            data = self.get_data_from_pool(key)
            if not data: continue

            avg = sum(data) / len(data) if len(data) > 0 else 0
            err_percent = (abs(avg - theo_val) / theo_val * 100) if theo_val != 0 else 0

            # 简化显示名字
            name = key.replace("r(cm)", "")
            print(f"{name:<10} | {avg:<10.4f} | {theo_val:<10.4f} | {err_percent:<10.2f}%")