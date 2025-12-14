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
    
    # D. 画图逻辑 (双表独立数据版)
    # ----------------------------------------------------
    TARGET_EXP_NAME = "磁滞回线 (H-B计算)"

    if calc_success and choice == TARGET_EXP_NAME:
        st.markdown("---")
        st.write("🔄 正在生成双表分析图表...")

        try:
            from scipy.interpolate import PchipInterpolator
            
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False

            # === 平滑函数 (PCHIP) ===
            def get_smooth_curve(x_in, y_in, num_points=300):
                if len(x_in) < 2: return x_in, y_in
                # 排序 (基本曲线必须排序)
                sorted_idx = np.argsort(x_in)
                x_s = x_in[sorted_idx]
                y_s = y_in[sorted_idx]
                # 插值
                try:
                    interpolator = PchipInterpolator(x_s, y_s)
                    x_smooth = np.linspace(x_s.min(), x_s.max(), num_points)
                    y_smooth = interpolator(x_smooth)
                    return x_smooth, y_smooth
                except:
                    return x_s, y_s

            # 获取数据
            # 1. 磁滞回线数据
            Loop_H = np.array(exp.get_data_from_pool("Loop_H", lambda: []))
            Loop_B = np.array(exp.get_data_from_pool("Loop_B", lambda: [])) * 1000 # T -> mT
            
            # 2. 基本特性数据
            Basic_H = np.array(exp.get_data_from_pool("Basic_H", lambda: []))
            Basic_B = np.array(exp.get_data_from_pool("Basic_B_mT", lambda: []))
            Basic_mu = np.array(exp.get_data_from_pool("Basic_mu", lambda: [])) * 1000 # H/m -> 10^-3 H/m

            if len(Loop_H) > 3 and len(Basic_H) > 3:
                st.markdown("### 📊 实验结果可视化")
                
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

                # ==========================================================
                # 左图: 磁滞回线 (来源于表2)
                # ==========================================================
                ax1.set_title("磁滞回线 (数据源: X-Y 格数)", fontsize=14)
                ax1.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                ax1.set_ylabel("磁感应强度 B (mT)", fontsize=12)
                
                # 磁滞回线平滑处理 (拆分上下支)
                mid = len(Loop_H) // 2
                # 下半支 (5 -> -5)
                h_bot, b_bot = get_smooth_curve(Loop_H[:mid+1], Loop_B[:mid+1])
                # 上半支 (-5 -> 5)
                h_top, b_top = get_smooth_curve(Loop_H[mid:], Loop_B[mid:])
                
                ax1.plot(h_bot, b_bot, 'k-', linewidth=1.5)
                ax1.plot(h_top, b_top, 'k-', linewidth=1.5, label='B-H Loop')
                ax1.scatter(Loop_H, Loop_B, color='red', s=30, zorder=5) # 原始点
                
                ax1.axhline(0, color='gray', linewidth=0.8, alpha=0.5)
                ax1.axvline(0, color='gray', linewidth=0.8, alpha=0.5)
                ax1.grid(True, linestyle='--', alpha=0.5)
                ax1.legend()

                # ==========================================================
                # 右图: 基本特性曲线 (来源于表1)
                # ==========================================================
                ax2.set_title("基本磁化曲线及导磁率 (数据源: H-B表)", fontsize=14)
                ax2.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                
                # 左Y轴: mu (红色)
                ax2.set_ylabel(r"磁导率 $\mu$ ($10^{-3}$ H/m)", color='red', fontsize=12)
                hx_mu, hy_mu = get_smooth_curve(Basic_H, Basic_mu)
                ax2.plot(hx_mu, hy_mu, 'r-', linewidth=2, label=r'$\mu$-H')
                ax2.scatter(Basic_H, Basic_mu, color='red', marker='s', s=30)
                ax2.tick_params(axis='y', labelcolor='red')
                
                # 右Y轴: B (蓝色)
                ax3 = ax2.twinx()
                ax3.set_ylabel("磁感应强度 B (mT)", color='blue', fontsize=12)
                hx_b, hy_b = get_smooth_curve(Basic_H, Basic_B)
                ax3.plot(hx_b, hy_b, 'b-', linewidth=2, label='B-H (Basic)')
                ax3.scatter(Basic_H, Basic_B, color='blue', marker='o', s=30)
                ax3.tick_params(axis='y', labelcolor='blue')
                
                # 合并图例
                lines = [plt.Line2D([0], [0], color='red', lw=2), plt.Line2D([0], [0], color='blue', lw=2)]
                ax2.legend(lines, [r'$\mu$-H', 'B-H (Basic)'], loc='center right')
                ax2.grid(True, linestyle='--', alpha=0.5)

                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.error("数据不足，无法绘图")

        except Exception as e:
            st.error(f"绘图出错: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
    


