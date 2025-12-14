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
# 实验 3: 磁滞回线
# ==============================================================================
hysteresis_pool = DependDecoratorPool()

class HysteresisExp(AbstractPhyExp):
    """
    磁滞回线实验类
    逻辑依据：
    1. 输入：示波器读取的 X格数 和 Y格数，以及实验装置参数。
    2. 计算：利用安培环路定理和RC积分电路原理，将格数转换为 H(磁场强度) 和 B(磁感应强度)。
    3. 输出：计算 Bm, Br, Hc 等关键指标，并生成绘图数据。
    """

    # === 1. 定义界面参数 ===
    # 这些变量名对应实验报告图片2顶部的"样品参数"和"装置参数"
    DATA_FLOAT = [
        # --- 样品参数 ---
        "L_m",          # 平均磁路长度 L (单位: m)
        "S_m2",         # 样品的截面积 S (单位: m^2)
        "N1",           # 励磁线圈匝数 N1
        "N2",           # 探测线圈匝数 N2
        
        # --- 装置参数 ---
        "Sx_V_div",     # 示波器 X轴灵敏度 (单位: V/div)
        "Sy_V_div",     # 示波器 Y轴灵敏度 (单位: V/div)
        "R1_Ohm",       # 采样电阻 R1 (单位: Ω)
        "R2_Ohm",       # 积分电阻 R2 (单位: Ω)
        "C_uF",         # 积分电容 C (单位: μF)
    ]
    
    # 定义列表数据：对应实验报告图片2表格中的 "X(格)" 和 "Y(格)"
    DATA_LIST = ["X_div_list", "Y_div_list"]

    # === 2. 初始化默认数据 ===
    def build_empty_data_json(self) -> None:
        """
        生成默认数据模板。
        数据来源：完全复刻实验报告图片2中的手写记录表。
        X轴逻辑：从 5.0 降到 -5.0，再升回 5.0，形成一个闭合回路。
        """
        # 构造闭合回路的 X 轴数据 (5.0 -> -5.0 -> 5.0)
        x_down = [5.0, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0]
        x_up   = [-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        # 拼接数组，去除重复的连接点，形成完整回线
        x_full = x_down + x_up[1:] 
        
        # 构造 Y 轴数据 (对应图片表格中的 Y读数)
        # y_down: 对应 X 从 5.0 到 -5.0 的过程
        y_down = [2.60, 2.50, 2.41, 2.11, 1.90, 1.60, 1.20, 0.51, -0.98, -2.12, -2.60]
        # y_up: 对应 X 从 -5.0 到 5.0 的过程
        y_up   = [-2.60, -2.50, -2.40, -2.15, -1.85, -1.58, -1.00, 0.00, 1.30, 2.12, 2.60]
        y_full = y_down + y_up[1:]

        template = {
            # --- 固定参数默认值 (源自报告图片顶端) ---
            "L_m": 0.084,
            "S_m2": 2.21e-4,
            "N1": 100,
            "N2": 300,
            "Sx_V_div": 0.1,
            "Sy_V_div": 0.1,
            "R1_Ohm": 2.0,       # 采样电阻
            "R2_Ohm": 1300.0,    # 积分电阻 (1.3k)
            "C_uF": 2.5,         # 积分电容
            
            # --- 测量数据 (转换为字符串格式以适配前端输入框) ---
            "X_div_list": [str(x) for x in x_full],
            "Y_div_list": [str(y) for y in y_full],
            
            "INFO": "数据来源于天津大学物理实验报告照片"
        }
        self._write_json(template)

    # === 3. 核心计算逻辑 ===
    @hysteresis_pool.depends()
    def calculate_BH(self):
        """
        根据实验报告中的物理公式进行计算：
        H = (N1 * Sx * X) / (L * R1)
        B = (R2 * C * Sy * Y) / (N2 * S)
        """
        # 1. 读取参数
        L = self.get_data_from_pool("L_m")
        S = self.get_data_from_pool("S_m2")
        N1 = self.get_data_from_pool("N1")
        N2 = self.get_data_from_pool("N2")
        Sx = self.get_data_from_pool("Sx_V_div")
        Sy = self.get_data_from_pool("Sy_V_div")
        R1 = self.get_data_from_pool("R1_Ohm")
        R2 = self.get_data_from_pool("R2_Ohm")
        C  = self.get_data_from_pool("C_uF") * 1e-6 # ⚠️ 重要：微法(uF) 转换为 法拉(F)

        # 2. 读取测量列表并转换为 Numpy 数组以便向量化计算
        x_raw = self.get_data_from_pool("X_div_list")
        y_raw = self.get_data_from_pool("Y_div_list")
        
        if not x_raw or not y_raw: return
        x = np.array(x_raw)
        y = np.array(y_raw)

        # 3. 计算转换系数 (对应报告图片2中的公式推导)
        # H 的系数: N1*Sx / (L*R1)
        coeff_H = (N1 * Sx) / (L * R1)
        
        # B 的系数: R2*C*Sy / (N2*S)
        coeff_B = (R2 * C * Sy) / (N2 * S)

        # 4. 批量计算 H (A/m) 和 B (T)
        H = x * coeff_H
        B = y * coeff_B

        # 5. 计算磁导率 mu = B / H
        # 用于绘制 μ-H 曲线。注意处理分母为0的情况。
        with np.errstate(divide='ignore', invalid='ignore'):
            mu = np.abs(B) / np.abs(H)
            mu[np.isinf(mu)] = 0 # 将无穷大置为0
            mu = np.nan_to_num(mu)

        # 6. 计算关键指标 (对应报告图片3底部的结果)
        # Bm: 饱和磁感应强度 (最大值)
        Bm = np.max(np.abs(B))
        
        # Br: 剩磁 (当 H=0 时的 B 值)
        # 在数据中寻找 X 最接近 0 的点取平均
        zero_x_indices = np.where(x == 0)[0]
        if len(zero_x_indices) > 0:
            Br = np.mean(np.abs(B[zero_x_indices]))
        else:
            Br = 0.0

        # Hc: 矫顽力 (当 B=0 时的 H 值)
        # 寻找 B 最接近 0 的位置对应的 H 值
        min_b_idx = np.argmin(np.abs(B))
        Hc = np.abs(H[min_b_idx]) 
        
        # 7. 打印计算过程表
        print(f"{'X(格)':<6} | {'H(A/m)':<10} | {'Y(格)':<6} | {'B(mT)':<10}")
        print("-" * 50)
        for i in range(len(x)):
            # B 显示为 mT (乘1000)
            print(f"{x[i]:<6.1f} | {H[i]:<10.2f} | {y[i]:<6.2f} | {B[i]*1000:<10.2f}")
            
        print("-" * 50)
        print(f"转换系数 coeff_H = {coeff_H:.4f}")
        print(f"转换系数 coeff_B = {coeff_B:.6f}")
        print(f"饱和磁感应强度 Bm ≈ {Bm*1000:.2f} mT")
        print(f"剩磁 Br         ≈ {Br*1000:.2f} mT")
        print(f"矫顽力 Hc       ≈ {Hc:.2f} A/m")

        # 8. 存储结果至数据池 (供前端绘图使用)
        self.data_pool["Results_H"] = H.tolist()
        self.data_pool["Results_B"] = B.tolist()
        self.data_pool["Results_mu"] = mu.tolist()

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

