import streamlit as st
import json
import io
import sys
import numpy as np
import matplotlib.pyplot as plt
from contextlib import redirect_stdout

# === 1. 导入所有实验类 ===
from experiments import (
    PendulumExp, pendulum_pool,
    OhmExp, ohm_pool,
    HysteresisExp, hysteresis_pool,
    ElectricFieldExp, cufield_pool
)

st.set_page_config(page_title="物理实验助手", layout="wide")
st.title("🧪 物理实验数据处理平台")

# === 2. 配置菜单 ===
experiments_map = {
    "单摆测重力加速度": (PendulumExp, "step2_average"),
    "伏安法测电阻": (OhmExp, "calc_R"),
    "磁滞回线 (H-B计算)": (HysteresisExp, "calculate_BH"),
    "静电场描绘 (r值均值误差)": (ElectricFieldExp, "calculate_results")
}

choice = st.sidebar.selectbox("请选择实验项目", list(experiments_map.keys()))

ExpClass, last_step_func_name = experiments_map[choice]
exp = ExpClass()

# ========================================================
# 🔑 关键配置：给每个实验指定不同的文件名
# ========================================================
exp.DATA_NAME = f"{ExpClass.__name__}.json"

# === 3. 预加载数据 ===
if not exp.load_data():
    exp.load_data()

# === 4. 生成界面 ===
st.header(choice)
st.info("👇 修改参数后点击开始计算")
user_data = {}
col1, col2 = st.columns(2)

# 处理单数值
if hasattr(exp, 'DATA_FLOAT'):
    for key in exp.DATA_FLOAT:
        with col1:
            default_val = exp.get_data_from_pool(key, lambda: 0.0)
            user_data[key] = st.number_input(f"{key}", value=float(default_val), format="%.4f")

# 处理列表
if hasattr(exp, 'DATA_LIST'):
    for key in exp.DATA_LIST:
        with col2:
            default_list = exp.get_data_from_pool(key, lambda: [])
            default_str = ", ".join([str(x) for x in default_list])
            val_str = st.text_area(f"{key} (逗号分隔)", value=default_str, height=100)
            try:
                items = val_str.replace('，', ',').split(',')
                user_data[key] = [x.strip() for x in items if x.strip()]
            except:
                st.error(f"{key} 格式错误")

# === 5. 运行与画图 ===
if st.button("开始计算", type="primary"):
    # A. 确保目录存在
    if not exp.get_target_path().exists(): exp.get_target_path().mkdir()

    # B. 保存数据
    save_data = user_data.copy()
    save_data['INFO'] = "UI Input"
    with open(str(exp.get_data_path()), 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=4)

    # C. 执行计算 (Try-Except 块只包裹计算过程)
    output_capture = io.StringIO()
    calc_success = False
    try:
        with redirect_stdout(output_capture):
            if exp.load_data():
                getattr(exp, last_step_func_name)()
                calc_success = True
        st.success("运行成功")
        st.code(output_capture.getvalue(), language='text')
    except Exception as e:
        st.error("运行出错")
        st.exception(e)

    # D. 画图逻辑 (注意：这里必须在 except 块的外面！！)
    # ----------------------------------------------------
    TARGET_EXP_NAME = "磁滞回线 (H-B计算)"

    if calc_success and choice == TARGET_EXP_NAME:
        st.markdown("---")  # 分割线
        st.write("🔄 正在尝试绘图...")  # 调试信息

        try:
            from scipy.interpolate import make_interp_spline

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False

            # 获取数据
            H_raw = exp.get_data_from_pool("Results_H", lambda: [])
            B_raw = exp.get_data_from_pool("Results_B", lambda: [])
            mu_raw = exp.get_data_from_pool("Results_mu", lambda: [])

            data_count = len(H_raw)
            st.write(f"📊 检测到数据点数量: {data_count}")

            if data_count >= 3:
                st.markdown("### 📊 实验图像 (双轴平滑曲线)")

                # --- 数据预处理 ---
                combined_data = sorted(zip(H_raw, B_raw, mu_raw))
                x = np.array([d[0] for d in combined_data])
                y1 = np.array([d[1] * 1000 for d in combined_data])  # 转 mT
                y2 = np.array([d[2] * 1000 for d in combined_data])  # 转 10^-3

                # --- 平滑处理逻辑 ---
                try:
                    x_smooth = np.linspace(x.min(), x.max(), 300)
                    k_value = 3 if data_count >= 4 else 2

                    spl_y1 = make_interp_spline(x, y1, k=k_value)
                    y1_smooth = spl_y1(x_smooth)

                    spl_y2 = make_interp_spline(x, y2, k=k_value)
                    y2_smooth = spl_y2(x_smooth)
                except Exception as e:
                    st.warning(f"平滑处理失败，降级为折线图: {e}")
                    x_smooth, y1_smooth, y2_smooth = x, y1, y2

                # --- 开始绘图 ---
                fig, ax1 = plt.subplots(figsize=(10, 6))

                # 左轴 B
                color_b = '#1f77b4'  # 经典蓝
                ax1.set_xlabel(' H (A/m)', fontsize=12)
                ax1.set_ylabel(' B (mT)', color=color_b, fontsize=12)
                line1, = ax1.plot(x_smooth, y1_smooth, color=color_b, linewidth=2, label='B-H ')
                ax1.scatter(x, y1, color=color_b, marker='o', s=50, zorder=5)  # 原始点
                ax1.tick_params(axis='y', labelcolor=color_b)
                ax1.grid(True, linestyle='--', alpha=0.5)

                # 右轴 mu
                ax2 = ax1.twinx()
                color_mu = '#ff7f0e'  # 经典橙
                ax2.set_ylabel(r' $\mu$ ($10^{-3}$ H/m)', color=color_mu, fontsize=12)
                line2, = ax2.plot(x_smooth, y2_smooth, color=color_mu, linewidth=2, linestyle='--',
                                  label='μ-H ')
                ax2.scatter(x, y2, color=color_mu, marker='s', s=50, zorder=5)  # 原始点
                ax2.tick_params(axis='y', labelcolor=color_mu)

                # 图例
                lines = [line1, line2]
                labels = [l.get_label() for l in lines]
                ax1.legend(lines, labels, loc='upper left', shadow=True)

               
                plt.tight_layout()

                # 显示图像
                st.pyplot(fig)

            else:
                st.error(f"❌ 数据点不足！当前只有 {data_count} 个点，至少需要 3 个点才能绘制曲线。")

        except ImportError:
            st.error("❌ 缺少必要的库。请在终端运行: pip install scipy numpy")
        except Exception as e:
            st.error(f"❌ 绘图过程发生未知错误: {e}")
            import traceback


            st.text(traceback.format_exc())
