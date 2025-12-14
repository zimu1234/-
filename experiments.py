from framework import AbstractPhyExp, DependDecoratorPool
import math

# ==============================================================================
# 实验 1: 单摆测重力加速度
# ==============================================================================
# 创建该实验专属的依赖管理器，防止与其他实验的任务混淆
pendulum_pool = DependDecoratorPool()


class PendulumExp(AbstractPhyExp):
    """
    单摆实验类
    逻辑：输入一组摆长(L)和对应的周期(T)，通过公式 g = 4*pi^2*L / T^2 计算重力加速度，最后求平均值。
    """

    # DATA_FLOAT 为空，表示本实验不需要输入单个的常数值
    DATA_FLOAT = []

    # DATA_LIST 定义了需要用户输入的列表数据。
    # 框架会根据这些 key 在界面上生成大文本框，用户输入逗号分隔的数据。
    DATA_LIST = ['L_list', 'T_list']

    def build_empty_data_json(self) -> None:
        """
        初始化默认数据。
        当首次运行或数据文件被删除时，系统会调用此方法生成模板文件。
        """
        template = {
            "L_list": ["1.00", "0.90", "0.80"],  # 默认摆长数据
            "T_list": ["2.01", "1.90", "1.79"],  # 默认周期数据
            "INFO": "L为摆长(m)，T为周期(s)"
        }
        self._write_json(template)

    @pendulum_pool.depends()
    def calculate_g(self):
        """
        核心计算任务：计算重力加速度 g
        """
        # 1. 从数据池中读取用户输入的数据，自动转换为 float 列表
        l_list = self.get_data_from_pool('L_list')
        t_list = self.get_data_from_pool('T_list')

        # 2. 数据校验：确保摆长和周期的数量一一对应
        if not self._check_lists_length(l_list, t_list):
            return

        # 3. 逐项计算
        g_results = []
        print(f"{'组别':<6} | {'摆长 L(m)':<12} | {'周期 T(s)':<12} | {'重力加速度 g':<15}")
        print("-" * 60)

        # 使用 zip 同时遍历两个列表
        for i, (l, t) in enumerate(zip(l_list, t_list)):
            # 防止除以零错误
            if t == 0: continue

            # 物理公式: g = 4 * pi^2 * L / T^2
            g = (4 * (math.pi ** 2) * l) / (t ** 2)
            g_results.append(g)

            # 打印单次测量结果
            print(f"{i + 1:<6} | {l:<12.4f} | {t:<12.4f} | {g:<15.4f}")

        # 4. 计算平均值并存储
        if g_results:
            avg_g = sum(g_results) / len(g_results)
            # 将结果存回 data_pool，以便后续可能的步骤使用
            self.data_pool['g_results'] = g_results
            print("-" * 60)
            print(f"平均重力加速度 g = {avg_g:.4f} m/s²")

    # --- 辅助方法 ---
    def _write_json(self, data):
        """辅助函数：将字典写入 JSON 文件"""
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _check_lists_length(self, list1, list2):
        """辅助函数：校验两个列表长度是否相等"""
        if len(list1) != len(list2):
            print(f"[错误] 数据长度不一致: {len(list1)} vs {len(list2)}")
            return False
        return True


# ==============================================================================
# 实验 2: 伏安法测电阻
# ==============================================================================
ohm_pool = DependDecoratorPool()


class OhmExp(AbstractPhyExp):
    """
    伏安法测电阻实验类
    逻辑：最简单的物理计算 R = U / I
    """

    # DATA_FLOAT 定义了单数值输入。
    # 框架会在界面上生成数字输入框 (Number Input)。
    DATA_FLOAT = ['U', 'I']
    DATA_LIST = []

    def build_empty_data_json(self) -> None:
        template = {
            "U": 10.0,  # 默认电压
            "I": 2.0,  # 默认电流
            "INFO": "U为电压(V)，I为电流(A)"
        }
        self._write_json(template)

    @ohm_pool.depends()
    def calculate_R(self):
        # 获取单数值
        u = self.get_data_from_pool('U')
        i = self.get_data_from_pool('I')

        print(f"输入参数: 电压 U = {u} V, 电流 I = {i} A")

        if i == 0:
            print("[错误] 电流 I 不能为 0")
            return

        # 欧姆定律计算
        r = u / i
        print("-" * 30)
        print(f"计算结果: 电阻 R = {r:.4f} Ω")

    def _write_json(self, data):
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


# ==============================================================================
# 实验 3: 磁滞回线
# ==============================================================================
hysteresis_pool = DependDecoratorPool()


class HysteresisExp(AbstractPhyExp):
    """
    磁滞回线实验类
    逻辑：涉及大量仪器常数（匝数、长度、截面积等）和一组示波器读数(X, Y)。
    需要将电学量(X, Y, U)转换为磁学量(H, B)。
    """

    # 定义所有固定的仪器参数
    DATA_FLOAT = ["N1", "N2", "l", "S", "Sx", "Sy", "R1", "R2", "C_uf"]
    # 定义变化的测量数据
    DATA_LIST = ["X_list", "Y_list"]

    def build_empty_data_json(self) -> None:
        template = {
            "N1": 100, "N2": 300,  # 线圈匝数
            "l": 0.084,  # 磁路平均长度 (m)
            "S": 2.21e-4,  # 截面积 (m^2)
            "Sx": 0.2, "Sy": 0.2,  # 示波器灵敏度
            "R1": 1.9, "R2": 1.1e3,  # 电阻值
            "C_uf": 2.0,  # 电容值 (微法)
            "X_list": ["0.5", "1.0", "1.5", "2.0"],
            "Y_list": ["0.8", "1.6", "2.4", "3.0"],
            "INFO": "输入示波器读取的X和Y格数"
        }
        self._write_json(template)

    @hysteresis_pool.depends()
    def calculate_BH(self):
        # 1. 获取仪器常数
        n1 = self.get_data_from_pool("N1")
        n2 = self.get_data_from_pool("N2")
        l = self.get_data_from_pool("l")
        s = self.get_data_from_pool("S")
        sx = self.get_data_from_pool("Sx")
        sy = self.get_data_from_pool("Sy")
        r1 = self.get_data_from_pool("R1")
        r2 = self.get_data_from_pool("R2")

        # 注意单位换算：微法 -> 法拉
        c = self.get_data_from_pool("C_uf") * 1e-6

        # 2. 获取测量列表
        x_list = self.get_data_from_pool("X_list")
        y_list = self.get_data_from_pool("Y_list")

        if len(x_list) != len(y_list):
            print("[错误] X和Y列表长度不一致")
            return

        print(f"{'No.':<4} | {'H (A/m)':<12} | {'B (T)':<12} | {'μ (H/m)':<12}")
        print("-" * 50)

        # 用于存储结果以便绘图
        res_H, res_B, res_mu = [], [], []

        for i, (x, y) in enumerate(zip(x_list, y_list)):
            # 计算磁场强度 H = (N1 * I1) / l = (N1 * X * Sx / R1) / l
            H = (n1 * x * sx) / (l * r1)

            # 计算磁感应强度 B = (R2 * C * U2) / (N2 * S) = (R2 * C * Y * Sy) / (N2 * S)
            B = (r2 * c * y * sy) / (n2 * s)

            # 计算磁导率 mu = B / H
            mu = B / H if H != 0 else 0

            res_H.append(H)
            res_B.append(B)
            res_mu.append(mu)
            print(f"{i + 1:<4} | {H:<12.4f} | {B:<12.6f} | {mu:<12.6e}")

        # 将结果存入 data_pool，供 app.py 中的画图模块调用
        self.data_pool["Results_H"] = res_H
        self.data_pool["Results_B"] = res_B
        self.data_pool["Results_mu"] = res_mu
        print("-" * 50)
        print("计算完成，请查看下方图像。")

    def _write_json(self, data):
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


# ==============================================================================
# 实验 4: 静电场描绘
# ==============================================================================
cufield_pool = DependDecoratorPool()


class ElectricFieldExp(AbstractPhyExp):
    """
    静电场描绘实验类
    逻辑：通过配置字典 (CONFIG) 动态生成需要输入的数据项。
    计算测量值与理论值的相对误差。
    """

    # 配置字典：定义了电压名称和对应的理论半径值
    CONFIG = {
        'r(cm)_7.5V': 1.38,
        'r(cm)_6.0V': 1.91,
        'r(cm)_4.5V': 2.63,
        'r(cm)_3.0V': 3.63,
        'r(cm)_1.5V': 5.05
    }

    DATA_FLOAT = []
    # 动态生成 DATA_LIST，使得代码扩展性极强，只需修改 CONFIG 即可增加测试项
    DATA_LIST = list(CONFIG.keys())

    def build_empty_data_json(self) -> None:
        # 动态生成模板，默认每组数据填 4 个 0
        template = {k: [0, 0, 0, 0] for k in self.DATA_LIST}
        template["INFO"] = "请输入各电压下测得的r值(cm)"
        self._write_json(template)

    @cufield_pool.depends()
    def calculate_results(self):
        print(f"{'电压项':<12} | {'测量均值':<10} | {'理论值':<10} | {'相对误差(%)':<12}")
        print("-" * 60)

        # 遍历配置项进行批量计算
        for key, theo_val in self.CONFIG.items():
            data = self.get_data_from_pool(key)

            if not data: continue

            # 计算平均值
            avg = sum(data) / len(data) if len(data) > 0 else 0

            # 计算相对误差: |测量 - 理论| / 理论
            err = abs(avg - theo_val)
            err_percent = (err / theo_val * 100) if theo_val != 0 else 0

            # 格式化输出名称 (去掉 Key 中冗余的字符)
            display_name = key.replace("r(cm)_", "")

            print(f"{display_name:<12} | {avg:<10.4f} | {theo_val:<10.4f} | {err_percent:<12.2f}%")

        print("-" * 60)

    def _write_json(self, data):
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


# ==============================================================================
# 实验 5: 光学干涉实验 (复刻天津大学实验报告逻辑)
# ==============================================================================
interference_pool = DependDecoratorPool()


class InterferenceExp(AbstractPhyExp):
    """
    光学干涉实验类
    包含两个子项目：
    1. 牛顿环测曲率半径 (逐差法，计算不确定度)
    2. 劈形膜测薄膜厚度
    """

    # === 1. 定义界面参数 ===
    DATA_FLOAT = [
        "Lambda_nm",  # 光源波长
        # --- 劈形膜相关参数 ---
        "Wedge_L_Right_mm",  # 劈尖长度 L 右读数
        "Wedge_L_Left_mm",  # 劈尖长度 L 左读数
        "Wedge_x_Right_mm",  # 条纹宽 x 右读数
        "Wedge_x_Left_mm",  # 条纹宽 x 左读数
        "Wedge_Count_N",  # 测量的条纹数量 N
    ]

    # DATA_LIST 定义牛顿环的测量数据 (分为 M 圈组 和 N 圈组)
    DATA_LIST = [
        "M_Order", "M_Left", "M_Right",  # 大圈级数、左读数、右读数
        "N_Order", "N_Left", "N_Right"  # 小圈级数、左读数、右读数
    ]

    # === 2. 初始化默认数据 (基于真实实验报告数据) ===
    def build_empty_data_json(self) -> None:
        template = {
            "Lambda_nm": 589.3,

            # --- 劈形膜数据 ---
            "Wedge_L_Right_mm": 37.201,
            "Wedge_L_Left_mm": 4.731,
            "Wedge_x_Right_mm": 24.000,
            "Wedge_x_Left_mm": 22.091,
            "Wedge_Count_N": 10,

            # --- 牛顿环数据 (M: 50-41环) ---
            "M_Order": [str(i) for i in range(50, 40, -1)],
            "M_Left": ["43.932", "43.883", "43.809", "43.759", "43.712", "43.625", "43.518", "43.439", "43.395",
                       "43.350"],
            "M_Right": ["32.544", "32.598", "32.655", "32.700", "32.762", "32.810", "32.877", "32.929", "32.986",
                        "33.042"],
            # --- 牛顿环数据 (N: 25-16环) ---
            "N_Order": [str(i) for i in range(25, 15, -1)],
            "N_Left": ["41.058", "40.965", "40.845", "40.735", "40.604", "40.519", "40.349", "40.195", "40.036",
                       "39.882"],
            "N_Right": ["34.061", "34.141", "34.218", "34.291", "34.356", "34.418", "34.520", "34.625", "34.698",
                        "34.770"],

            "INFO": "数据来源于实验报告图片"
        }
        self._write_json(template)

    # === 3. 计算牛顿环曲率半径 ===
    @interference_pool.depends()
    def calculate_newton_R(self):
        print(f"\n{'=' * 30} 项目 1: 牛顿环 (Newton's Rings) {'=' * 30}")

        # 获取波长并换算为米
        lam = self.get_data_from_pool("Lambda_nm") * 1e-9

        # 获取 M 组和 N 组的列表数据
        m_orders, m_left, m_right = self.get_data_from_pool("M_Order"), self.get_data_from_pool(
            "M_Left"), self.get_data_from_pool("M_Right")
        n_orders, n_left, n_right = self.get_data_from_pool("N_Order"), self.get_data_from_pool(
            "N_Left"), self.get_data_from_pool("N_Right")

        # 校验两组数据长度必须一致
        count = len(m_orders)
        if len(n_orders) != count: return

        print(f"{'序号':<4} | {'M-N':<5} | {'dm (mm)':<10} | {'dn (mm)':<10} | {'dm^2-dn^2':<12} | {'R (m)':<10}")
        print("-" * 75)

        R_list = []
        for i in range(count):
            m, n = m_orders[i], n_orders[i]

            # 计算直径 d = |左读数 - 右读数| (单位 mm)
            dm_mm, dn_mm = abs(m_left[i] - m_right[i]), abs(n_left[i] - n_right[i])

            # 换算为米以便进行物理计算
            dm_met, dn_met = dm_mm * 1e-3, dn_mm * 1e-3

            # 计算直径平方差 (Dm^2 - Dn^2)
            diff_D2_met = (dm_met ** 2) - (dn_met ** 2)
            # 为了对应实验报告上的数值，转换回 mm^2 显示
            diff_D2_mm2 = diff_D2_met * 1e6

            diff_order = m - n
            if diff_order == 0: continue

            # 核心公式: R = (Dm^2 - Dn^2) / (4 * (m-n) * lambda)
            R = diff_D2_met / (4 * diff_order * lam)
            R_list.append(R)

            print(
                f"{i + 1:<4} | {int(diff_order):<5} | {dm_mm:<10.3f} | {dn_mm:<10.3f} | {diff_D2_mm2:<12.3f} | {R:.4f}")

        # 统计分析 (计算不确定度)
        n_count = len(R_list)
        if n_count > 1:
            # 1. 计算平均值
            avg_R = sum(R_list) / n_count

            # 2. 计算A类不确定度 U_A (贝塞尔公式)
            sum_sq_diff = sum([(r - avg_R) ** 2 for r in R_list])
            U_A = math.sqrt(sum_sq_diff / (n_count * (n_count - 1)))

            # 3. 计算相对不确定度
            U_r_percent = (U_A / avg_R) * 100 if avg_R != 0 else 0

            print("-" * 75)
            print(f"平均值 R_bar = {avg_R:.4f} m")
            print(f"A类不确定度 U_A = {U_A:.4f} m")
            print(f"结果: R = {avg_R:.4f} ± {U_A:.4f} m")

            # 存结果
            self.data_pool["Results_R"] = avg_R

    # === 4. 计算劈形膜厚度 ===
    # 依赖关系：点击按钮时，会先执行 calculate_newton_R，再执行本函数
    @interference_pool.depends(calculate_newton_R)
    def calculate_wedge_thickness(self):
        print(f"\n{'=' * 30} 项目 2: 薄膜厚度 (Wedge Thickness) {'=' * 30}")

        # 获取参数
        lam_nm = self.get_data_from_pool("Lambda_nm")
        l_right = self.get_data_from_pool("Wedge_L_Right_mm")
        l_left = self.get_data_from_pool("Wedge_L_Left_mm")
        x_right = self.get_data_from_pool("Wedge_x_Right_mm")
        x_left = self.get_data_from_pool("Wedge_x_Left_mm")
        N = self.get_data_from_pool("Wedge_Count_N")

        if N == 0:
            print("条纹数 N 不能为 0")
            return

        # 计算劈尖长度 L = |右 - 左|
        val_L = abs(l_right - l_left)

        # 计算条纹总宽 x = |右 - 左|
        val_x = abs(x_right - x_left)

        # 计算单条纹间距 Δx = x / N
        delta_x = val_x / N

        print(f"L (劈尖长) = |{l_right} - {l_left}| = {val_L:.3f} mm")
        print(f"x (条纹宽) = |{x_right} - {x_left}| = {val_x:.3f} mm")
        print(f"Δx (间距)  = {val_x:.3f} / {int(N)} ≈ {delta_x:.4f} mm")

        # 单位换算：波长转为 mm
        lam_mm = lam_nm * 1e-6

        if delta_x == 0:
            print("Δx 为 0，无法计算")
            return

        # 核心公式: t = (L / Δx) * (λ / 2)
        t_mm = (val_L / delta_x) * (lam_mm / 2)

        print("-" * 60)
        print(f"计算公式: t = (L / Δx) * (λ / 2)")
        print(f"代入数值: t = ({val_L:.3f} / {delta_x:.4f}) * ({lam_mm:.7f} / 2)")
        print(f"最终结果: t = {t_mm:.5f} mm")

        self.data_pool["Results_t_mm"] = t_mm

    def _write_json(self, data):
        import json
        with open(str(self.get_data_path()), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
