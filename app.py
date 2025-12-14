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

    # --- C. 绘图逻辑 (仅针对磁滞回线实验) ---
    # 注意：绘图代码必须放在 try-except 块之外，确保计算成功后才执行
    TARGET_EXP_NAME = "磁滞回线 (H-B计算)"

    if calc_success and choice == TARGET_EXP_NAME:
        st.markdown("---")
        st.write("🔄 正在尝试绘图...")

        try:
            # 引入插值库用于绘制平滑曲线
            from scipy.interpolate import make_interp_spline

            # 设置字体配置，防止中文乱码 (尝试多种常用中文字体)
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False

            # 从数据池获取计算结果
            H_raw = exp.get_data_from_pool("Results_H", lambda: [])
            B_raw = exp.get_data_from_pool("Results_B", lambda: [])
            mu_raw = exp.get_data_from_pool("Results_mu", lambda: [])

            data_count = len(H_raw)
            st.write(f"📊 检测到数据点数量: {data_count}")

            # 只有数据点足够多时才绘图
            if data_count >= 3:
                st.markdown("### 📊 实验图像 (双轴平滑曲线)")

                # 1. 数据预处理：排序与单位转换
                # 必须按 H 排序，否则插值曲线会混乱
                combined_data = sorted(zip(H_raw, B_raw, mu_raw))
                x = np.array([d[0] for d in combined_data])  # H (A/m)
                y1 = np.array([d[1] * 1000 for d in combined_data])  # B (mT)
                y2 = np.array([d[2] * 1000 for d in combined_data])  # mu (10^-3)

                # 2. 平滑插值处理
                try:
                    # 创建更密集的 X 轴坐标点 (300个)
                    x_smooth = np.linspace(x.min(), x.max(), 300)
                    # 根据点数选择插值阶数 (点多用3阶，点少用2阶)
                    k_value = 3 if data_count >= 4 else 2

                    spl_y1 = make_interp_spline(x, y1, k=k_value)
                    y1_smooth = spl_y1(x_smooth)

                    spl_y2 = make_interp_spline(x, y2, k=k_value)
                    y2_smooth = spl_y2(x_smooth)
                except Exception as e:
                    # 如果插值失败，降级为使用原始折线数据
                    st.warning(f"平滑处理失败，降级为折线图: {e}")
                    x_smooth, y1_smooth, y2_smooth = x, y1, y2

                # 3. 绘制双 Y 轴图表
                fig, ax1 = plt.subplots(figsize=(10, 6))

                # --- 左轴 (B-H) ---
                color_b = '#1f77b4'  # 蓝色
                ax1.set_xlabel('磁场强度 H (A/m)', fontsize=12)
                ax1.set_ylabel('磁感应强度 B (mT)', color=color_b, fontsize=12)
                line1, = ax1.plot(x_smooth, y1_smooth, color=color_b, linewidth=2, label='B-H 曲线')
                ax1.scatter(x, y1, color=color_b, marker='o', s=50, zorder=5)  # 原始数据点
                ax1.tick_params(axis='y', labelcolor=color_b)
                ax1.grid(True, linestyle='--', alpha=0.5)

                # --- 右轴 (mu-H) ---
                ax2 = ax1.twinx()  # 共享 X 轴
                color_mu = '#ff7f0e'  # 橙色
                ax2.set_ylabel(r'磁导率 $\mu$ ($10^{-3}$ H/m)', color=color_mu, fontsize=12)
                line2, = ax2.plot(x_smooth, y2_smooth, color=color_mu, linewidth=2, linestyle='--', label='μ-H 曲线')
                ax2.scatter(x, y2, color=color_mu, marker='s', s=50, zorder=5)  # 原始数据点
                ax2.tick_params(axis='y', labelcolor=color_mu)

                # --- 合并图例 ---
                lines = [line1, line2]
                labels = [l.get_label() for l in lines]
                ax1.legend(lines, labels, loc='upper left', shadow=True)

                plt.tight_layout()
                st.pyplot(fig)  # 在 Streamlit 中显示图表

            else:
                st.error(f"❌ 数据点不足！当前只有 {data_count} 个点，至少需要 3 个点才能绘制曲线。")

        except ImportError:
            st.error("❌ 缺少必要的库。请在终端运行: pip install scipy numpy")
        except Exception as e:
            st.error(f"❌ 绘图过程发生未知错误: {e}")
            import traceback

            st.text(traceback.format_exc())



