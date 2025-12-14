from framework import AbstractPhyExp, DependDecoratorPool
import math
import numpy as np
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
# 实验 3: 磁滞回线 (双表数据版)
# 表1: 基本磁化曲线 (H, B) -> 画右图
# 表2: 磁滞回线 (X, Y)    -> 画左图
# ==============================================================================
hysteresis_pool = DependDecoratorPool()

class HysteresisExp(AbstractPhyExp):
    # === 1. 定义界面参数 ===
    DATA_FLOAT = [
        # 装置参数 (用于计算磁滞回线)
        "L_m", "S_m2", "N1", "N2",
        "Sx_V_div", "Sy_V_div", "R1_Ohm", "R2_Ohm", "C_uF"
    ]
    
   
    DATA_LIST = [
        # --- 表1: 基本磁化曲线数据 (直接输入 H 和 B) ---
        "Table1_H_Am",   # H (A/m)
        "Table1_B_mT",   # B (mT)
        
        # --- 表2: 磁滞回线数据 (输入示波器格数) ---
        "Table2_X_div",  # X (格)
        "Table2_Y_div"   # Y (格)
    ]

    # === 2. 初始化默认数据  ===
    def build_empty_data_json(self) -> None:
        # --- 表2数据 (磁滞回线 X, Y) ---
        # 闭合回路: 5.0 -> -5.0 -> 5.0
        x_down = [5.0, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0]
        x_up   = [-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        x_loop = x_down + x_up[1:]
        
        y_down = [2.60, 2.50, 2.41, 2.11, 1.90, 1.60, 1.20, 0.51, -0.98, -2.12, -2.60]
        y_up   = [-2.60, -2.50, -2.40, -2.15, -1.85, -1.58, -1.00, 0.00, 1.30, 2.12, 2.60]
        y_loop = y_down + y_up[1:]

        # --- 表1数据 (基本磁化曲线 H, B) ---
       
        basic_H = [11.9, 23.81, 35.71, 47.62, 59.52, 89.28, 119.04, 148.8, 178.56, 238.08, 297.6]
        basic_B = [3.43, 6.86, 10.78, 12.25, 15.68, 26.95, 41.16, 61.25, 77.42, 106.33, 127.4]

        template = {
            # 装置参数
            "L_m": 0.084, "S_m2": 2.21e-4, "N1": 100, "N2": 300,
            "Sx_V_div": 0.1, "Sy_V_div": 0.1,
            "R1_Ohm": 2.0, "R2_Ohm": 1300.0, "C_uF": 2.5,
            
            # 表1: 基本特性
            "Table1_H_Am": [str(x) for x in basic_H],
            "Table1_B_mT": [str(x) for x in basic_B],
            
            # 表2: 磁滞回线
            "Table2_X_div": [str(x) for x in x_loop],
            "Table2_Y_div": [str(x) for x in y_loop],
            
        }
        self._write_json(template)

    # === 3. 计算逻辑 ===
    @hysteresis_pool.depends()
    def calculate_BH(self):
        # --- A. 处理表2：磁滞回线 (Loop) ---
        # 读取示波器格数
        x_raw = self.get_data_from_pool("Table2_X_div")
        y_raw = self.get_data_from_pool("Table2_Y_div")
        
        if x_raw and y_raw:
            x = np.array(x_raw)
            y = np.array(y_raw)
            
            # 读取参数计算系数
            L, S = self.get_data_from_pool("L_m"), self.get_data_from_pool("S_m2")
            N1, N2 = self.get_data_from_pool("N1"), self.get_data_from_pool("N2")
            Sx, Sy = self.get_data_from_pool("Sx_V_div"), self.get_data_from_pool("Sy_V_div")
            R1, R2 = self.get_data_from_pool("R1_Ohm"), self.get_data_from_pool("R2_Ohm")
            C = self.get_data_from_pool("C_uF") * 1e-6

            # 公式计算 H 和 B
            H_loop = x * (N1 * Sx) / (L * R1)
            B_loop = y * (R2 * C * Sy) / (N2 * S)
            
            # 存入 Loop 结果
            self.data_pool["Loop_H"] = H_loop.tolist()
            self.data_pool["Loop_B"] = B_loop.tolist()
            
            print(f"磁滞回线计算完成，共 {len(x)} 个点")

        # --- B. 处理表1：基本磁化曲线 (Basic) ---
        # 直接读取用户输入的 H(A/m) 和 B(mT)
        h_basic_raw = self.get_data_from_pool("Table1_H_Am")
        b_basic_raw = self.get_data_from_pool("Table1_B_mT")
        
        if h_basic_raw and b_basic_raw:
            H_basic = np.array(h_basic_raw)
            B_basic_mT = np.array(b_basic_raw)
            
            # 计算磁导率 mu = B / H
            # 注意单位：B输入是mT，公式需要T。mu单位通常是 H/m
            B_basic_T = B_basic_mT / 1000.0
            
            with np.errstate(divide='ignore', invalid='ignore'):
                mu_basic = B_basic_T / H_basic
                mu_basic[np.isinf(mu_basic)] = 0
                mu_basic = np.nan_to_num(mu_basic)
            
            # 存入 Basic 结果
            self.data_pool["Basic_H"] = H_basic.tolist()
            self.data_pool["Basic_B_mT"] = B_basic_mT.tolist()
            self.data_pool["Basic_mu"] = mu_basic.tolist()
            
            print(f"基本磁化曲线计算完成，共 {len(H_basic)} 个点")
            print(f"{'H(A/m)':<8} | {'B(mT)':<8} | {'mu(H/m)':<10}")
            for h, b, m in zip(H_basic, B_basic_mT, mu_basic):
                print(f"{h:<8.2f} | {b:<8.2f} | {m:.2e}")

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


