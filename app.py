import streamlit as st
import json
import io
import sys
import numpy as np
import matplotlib.pyplot as plt
from contextlib import redirect_stdout

# ==============================================================================
# 1. 核心模块导入
# 导入 experiments.py 中定义的所有实验类及其对应的任务池
# ==============================================================================
from experiments import (
    PendulumExp, pendulum_pool,
    OhmExp, ohm_pool,
    HysteresisExp, hysteresis_pool,
    ElectricFieldExp, cufield_pool,
    InterferenceExp, interference_pool
)

# ==============================================================================
# 2. 页面基础设置
# 设置网页标题、布局模式（wide模式可以容纳更宽的图表）
# ==============================================================================
st.set_page_config(page_title="物理实验助手", layout="wide")
st.title("🧪 物理实验数据处理平台")

# ==============================================================================
# 3. 实验菜单配置
# 映射关系： "菜单显示名称" : (对应的实验类, 点击按钮后执行的入口函数名)
# ==============================================================================
experiments_map = {
    "单摆测重力加速度": (PendulumExp, "step2_average"),
    "伏安法测电阻": (OhmExp, "calc_R"),
    "磁滞回线 (H-B计算)": (HysteresisExp, "calculate_BH"),
    "静电场描绘 (r值均值误差)": (ElectricFieldExp, "calculate_results"),
    "光学干涉 (牛顿环 & 劈形膜)": (InterferenceExp, "calculate_wedge_thickness")
}

# 侧边栏下拉框，供用户选择实验
choice = st.sidebar.selectbox("请选择实验项目", list(experiments_map.keys()))

# 根据选择，获取对应的类和函数名，并实例化对象
ExpClass, last_step_func_name = experiments_map[choice]
exp = ExpClass()

# ==============================================================================
# 4. 数据隔离策略
# 强制指定数据文件名。例如单摆实验只读写 PendulumExp.json，防止数据污染。
# ==============================================================================
exp.DATA_NAME = f"{ExpClass.__name__}.json"

# ==============================================================================
# 5. 数据预加载逻辑
# 尝试加载数据。如果文件不存在，框架会自动生成带默认值的 JSON 模板。
# 再次加载是为了将刚生成的默认值读入内存，以便显示在下方的输入框中。
# ==============================================================================
if not exp.load_data():
    exp.load_data()

# ==============================================================================
# 6. 动态生成输入界面
# 遍历实验类中定义的 DATA_FLOAT (单数值) 和 DATA_LIST (列表值)
# ==============================================================================
st.header(choice)
st.info("👇 修改参数后点击开始计算")

# 用于临时存储用户在网页上输入的数据
user_data = {}
col1, col2 = st.columns(2)

# --- 动态生成数字输入框 (针对单个物理量) ---
if hasattr(exp, 'DATA_FLOAT'):
    for key in exp.DATA_FLOAT:
        with col1:
            # 获取默认值，如果获取失败则默认为 0.0
            default_val = exp.get_data_from_pool(key, lambda: 0.0)
            user_data[key] = st.number_input(f"{key}", value=float(default_val), format="%.4f")

# --- 动态生成文本区域 (针对列表数据) ---
if hasattr(exp, 'DATA_LIST'):
    for key in exp.DATA_LIST:
        with col2:
            # 获取默认列表，并转换为逗号分隔的字符串显示
            default_list = exp.get_data_from_pool(key, lambda: [])
            default_str = ", ".join([str(x) for x in default_list])

            val_str = st.text_area(f"{key} (逗号分隔)", value=default_str, height=100)

            # 将用户输入的字符串解析回列表
            try:
                # 兼容中文逗号，分割并去除空格
                items = val_str.replace('，', ',').split(',')
                user_data[key] = [x.strip() for x in items if x.strip()]
            except:
                st.error(f"{key} 格式错误")

# ==============================================================================
# 7. 运行逻辑
# 点击按钮后：保存界面数据 -> 执行后端计算 -> 捕获打印输出 -> 绘图
# ==============================================================================
if st.button("开始计算", type="primary"):

    # --- A. 保存数据 ---
    # 确保目标文件夹存在
    if not exp.get_target_path().exists(): exp.get_target_path().mkdir()

    # 将用户界面上的数据写入 JSON 文件
    save_data = user_data.copy()
    save_data['INFO'] = "UI Input"
    with open(str(exp.get_data_path()), 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=4)

    # --- B. 执行计算 & 捕获输出 ---
    # 使用 StringIO 捕获后端逻辑中的 print() 内容
    output_capture = io.StringIO()
    calc_success = False

    try:
        with redirect_stdout(output_capture):
            # 重新从文件加载数据（确保后端使用的是最新保存的数据）
            if exp.load_data():
                # 动态调用实验入口函数 (例如 calculate_BH)
                getattr(exp, last_step_func_name)()
                calc_success = True

        # 在网页上显示捕获的计算日志
        st.success("运行成功")
        st.code(output_capture.getvalue(), language='text')

    except Exception as e:
        st.error("运行出错")
        st.exception(e)
    
    # D. 画图逻辑 (优化版：平滑曲线 + 字体修复 + 数据排序)
    # ----------------------------------------------------
    TARGET_EXP_NAME = "磁滞回线 (H-B计算)"

    if calc_success and choice == TARGET_EXP_NAME:
        st.markdown("---")
        st.write("🔄 正在生成平滑曲线图表...")

        try:
            from scipy.interpolate import make_interp_spline
            
            # === 1. 全局字体设置 (解决中文乱码) ===
            # 优先尝试 Windows/Linux/Mac 常见中文字体
            possible_fonts = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'WenQuanYi Micro Hei', 'sans-serif']
            plt.rcParams['font.sans-serif'] = possible_fonts
            plt.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题

            # === 2. 获取原始数据 ===
            H = np.array(exp.get_data_from_pool("Results_H", lambda: []))
            # 转换为显示单位: B(mT), mu(10^-3)
            B = np.array(exp.get_data_from_pool("Results_B", lambda: [])) * 1000 
            mu = np.array(exp.get_data_from_pool("Results_mu", lambda: [])) * 1000 

            # 定义一个通用的平滑函数
            def get_smooth_data(x_raw, y_raw, k=3, num_points=300):
                """
                x_raw, y_raw: 原始数据
                k: 插值阶数 (3为三次样条，曲线最滑)
                num_points: 插值后的点数
                """
                # 1. 必须按 x 排序，否则插值会报错或乱画
                sorted_indices = np.argsort(x_raw)
                x_sorted = x_raw[sorted_indices]
                y_sorted = y_raw[sorted_indices]
                
                # 2. 去除 x 重复的点 (插值不允许 x 有重复)
                x_unique, unique_indices = np.unique(x_sorted, return_index=True)
                y_unique = y_sorted[unique_indices]
                
                # 3. 数据点过少时降级处理
                if len(x_unique) <= k:
                    return x_sorted, y_sorted # 点太少，直接返回折线
                
                # 4. 生成插值
                try:
                    spl = make_interp_spline(x_unique, y_unique, k=k)
                    x_smooth = np.linspace(x_unique.min(), x_unique.max(), num_points)
                    y_smooth = spl(x_smooth)
                    return x_smooth, y_smooth
                except:
                    return x_sorted, y_sorted

            if len(H) > 4:
                st.markdown("### 📊 实验结果可视化 (平滑处理)")
                
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

                # ==========================================================
                # 图1: 磁滞回线 (B-H Loop) - 平滑处理技巧
                # 技巧：磁滞回线不能直接排序(否则会变成一条线)，需要拆分成"上行"和"下行"两段分别平滑
                # ==========================================================
                ax1.set_title("磁滞回线 (B-H Loop)", fontsize=14)
                ax1.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                ax1.set_ylabel("磁感应强度 B (mT)", fontsize=12)
                
                # 找到 X 轴最大值和最小值的索引，将回线切分为两半
                # 通常数据是 5 -> -5 -> 5。最大值在两头，最小值在中间。
                idx_max = np.argmax(H) # 理论上是起点附近
                idx_min = np.argmin(H) # 理论上是中间
                
                # 由于数据可能是环状数组，我们简单地将其对半切分
                mid_point = len(H) // 2
                
                # 上半支 (从正到负)
                h_top_raw = H[:mid_point+1]
                b_top_raw = B[:mid_point+1]
                # 下半支 (从负到正)
                h_bot_raw = H[mid_point:]
                b_bot_raw = B[mid_point:]
                
                # 分别获取平滑曲线
                h_top_smooth, b_top_smooth = get_smooth_data(h_top_raw, b_top_raw)
                h_bot_smooth, b_bot_smooth = get_smooth_data(h_bot_raw, b_bot_raw)
                
                # 绘制平滑线
                ax1.plot(h_top_smooth, b_top_smooth, '-', color='black', linewidth=1.5, label='Fit Curve')
                ax1.plot(h_bot_smooth, b_bot_smooth, '-', color='black', linewidth=1.5)
                
                # 绘制原始散点
                ax1.scatter(H, B, color='red', s=30, zorder=5, label='Raw Data')
                
                ax1.axhline(0, color='gray', linewidth=0.8, alpha=0.5)
                ax1.axvline(0, color='gray', linewidth=0.8, alpha=0.5)
                ax1.grid(True, linestyle='--', alpha=0.5)
                ax1.legend(loc='upper left')

                # ==========================================================
                # 图2: 基本磁化曲线与导磁率 - 必须排序
                # ==========================================================
                ax2.set_title("基本磁化曲线及导磁率", fontsize=14)
                ax2.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                
                # 筛选第一象限数据 (H>0, B>0)
                mask = (H > 1e-3) & (B > 1e-3) # 过滤掉0值防止干扰
                h_pos = H[mask]
                mu_pos = mu[mask]
                b_pos = B[mask]

                if len(h_pos) > 3:
                    # --- 左Y轴: mu (红色) ---
                    ax2.set_ylabel(r"磁导率 $\mu$ ($10^{-3}$ H/m)", color='red', fontsize=12)
                    
                    # 获取平滑数据 (函数内部会自动排序)
                    h_mu_smooth, mu_smooth = get_smooth_data(h_pos, mu_pos)
                    
                    ax2.plot(h_mu_smooth, mu_smooth, '-', color='red', linewidth=2, label=r'$\mu$-H')
                    ax2.scatter(h_pos, mu_pos, color='red', marker='s', s=30) # 原始点
                    ax2.tick_params(axis='y', labelcolor='red')
                    
                    # --- 右Y轴: B (蓝色) ---
                    ax3 = ax2.twinx()
                    ax3.set_ylabel("磁感应强度 B (mT)", color='blue', fontsize=12)
                    
                    # 获取平滑数据
                    h_b_smooth, b_b_smooth = get_smooth_data(h_pos, b_pos)
                    
                    ax3.plot(h_b_smooth, b_b_smooth, '-', color='blue', linewidth=2, label='B-H (Basic)')
                    ax3.scatter(h_pos, b_pos, color='blue', marker='o', s=30) # 原始点
                    ax3.tick_params(axis='y', labelcolor='blue')
                    
                    # 合并图例
                    lines = [plt.Line2D([0], [0], color='red', lw=2), plt.Line2D([0], [0], color='blue', lw=2)]
                    ax2.legend(lines, [r'$\mu$-H', 'B-H (Basic)'], loc='center right')
                
                ax2.grid(True, linestyle='--', alpha=0.5)

                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.error("数据点不足 (至少需要 5 个点才能进行平滑绘制)")

        except ImportError:
            st.error("缺少必要的库，请安装: pip install scipy")
        except Exception as e:
            st.error(f"绘图出错: {e}")
            import traceback
            st.text(traceback.format_exc())
    

