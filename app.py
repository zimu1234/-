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
        st.write("🔄 正在生成分析图表...")

        try:
            from scipy.interpolate import make_interp_spline
            
            # 设置绘图字体 (优先使用 SimHei 显示中文，没有则回退到其他字体)
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False

            # 获取计算结果
            H = np.array(exp.get_data_from_pool("Results_H", lambda: []))
            # 将 B 转换为 mT，将 mu 转换为 10^-3 单位，以匹配实验报告的坐标轴数值
            B = np.array(exp.get_data_from_pool("Results_B", lambda: [])) * 1000 
            mu = np.array(exp.get_data_from_pool("Results_mu", lambda: [])) * 1000 

            if len(H) > 3:
                st.markdown("### 📊 实验结果可视化")
                
                # 创建 1 行 2 列的子图布局，figsize设置图片宽长比
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

                # === 图1: 磁滞回线 (B-H Loop) ===
                # 复刻实验报告图片3的效果
                ax1.set_title("磁滞回线 (B-H Loop)", fontsize=14)
                ax1.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                ax1.set_ylabel("磁感应强度 B (mT)", fontsize=12)
                
                # 绘制闭合回路，zorder控制绘制层级
                ax1.plot(H, B, 'o-', color='black', linewidth=1.5, label='Loop', zorder=2)
                
                # 绘制十字坐标轴辅助线
                ax1.axhline(0, color='gray', linewidth=0.8, zorder=1) 
                ax1.axvline(0, color='gray', linewidth=0.8, zorder=1)
                ax1.grid(True, linestyle='--', alpha=0.5)

                # === 图2: 基本磁化曲线与导磁率 (u-H & B-H) ===
                # 复刻实验报告图片1的效果：双Y轴显示
                ax2.set_title("基本磁化曲线及导磁率", fontsize=14)
                ax2.set_xlabel("磁场强度 H (A/m)", fontsize=12)
                
                # 左Y轴：绘制磁导率 mu (红色)
                ax2.set_ylabel(r"磁导率 $\mu$ ($10^{-3}$ H/m)", color='red', fontsize=12)
                
                # 数据筛选：只取第一象限 (H>0, B>0) 的数据来绘制基本特性
                mask = (H > 0) & (B > 0)
                h_pos = H[mask]
                mu_pos = mu[mask]
                b_pos = B[mask]
                
                # 排序：按 H 从小到大排序，防止连线错乱
                sorted_indices = np.argsort(h_pos)
                h_sorted = h_pos[sorted_indices]
                mu_sorted = mu_pos[sorted_indices]
                b_sorted = b_pos[sorted_indices]
                
                # 绘制 mu-H 曲线
                ax2.plot(h_sorted, mu_sorted, 's-', color='red', label=r'$\mu$-H')
                ax2.tick_params(axis='y', labelcolor='red')
                
                # 右Y轴：绘制基本磁化 B-H (蓝色)
                ax3 = ax2.twinx() # 创建共享X轴的第二个坐标轴
                ax3.set_ylabel("磁感应强度 B (mT)", color='blue', fontsize=12)
                ax3.plot(h_sorted, b_sorted, 'o-', color='blue', label='B-H (Basic)')
                ax3.tick_params(axis='y', labelcolor='blue')
                
                ax2.grid(True, linestyle='--', alpha=0.5)

                plt.tight_layout() # 自动调整间距防止重叠
                st.pyplot(fig)     # 在网页显示图片
            else:
                st.error("数据点不足，无法绘图")

        except Exception as e:
            st.error(f"绘图出错: {e}")
            import traceback
            st.text(traceback.format_exc())




