# 六个可复制演示提示词 / Six copy-ready demo prompts

这些提示词与首页「经典模型示例 / Model examples」按钮一致。先在左上角选择 ASPECT 或 I2VIS；层析图与论文案例需先在对话框上传相应附件。短程运行只验证输入与起始演化，不构成论文复现或收敛证明。

These are the exact prompts used by the homepage Model examples menu. Choose ASPECT or I2VIS first and attach the required tomography image or paper before sending. A short pilot verifies startup behavior, not a published result or convergence.

录屏建议：先展示三组 Ra 的模型创建、初始场和完成状态，再展示 I2VIS 密度差与热柱。层析图需提前准备清晰色标、坐标、单位及转换关系；论文案例需准备 PDF 和缺失参数。660 km 相变与论文三维模型适合作为进阶片段，在参数对齐与运行通过后再录制。求解器已通过的模型不代表任意聊天模型都会一次生成正确输入；录制前请用你实际选用的 API 模型完整排练一次。

For recording, start with the three-Ra workflow and the I2VIS density/plume templates. Prepare calibration data for tomography and the PDF plus missing parameters for a paper model. Record the phase-transition and 3D paper segments after their inputs and physics are reviewed. Rehearse with your chosen API model: successful solver tests do not guarantee every chat provider will generate the same inputs.

## ASPECT 1 · 三组 Ra 热对流 / Three Rayleigh numbers

中文：

```text
请基于已安装的 ASPECT 3.1.0 convection-box 完整算例，建立三个 1000×500 km 的二维 Boussinesq 热对流模型。四边速度自由滑移，左右绝热，顶部/底部固定为 273/1573 K；三个模型使用相同的线性初始地温和小幅扰动。目标 Ra 分别为 10^2、10^4、10^5，只通过黏度改变 Ra。教学取值为 rho=3300 kg/m^3、alpha=3e-5 K^-1、Cp=1250 J/(kg K)、k=4.125 W/(m K)、g=9.81 m/s^2，因此 kappa=1e-6 m^2/s。按 Ra=rho*g*alpha*DeltaT*H^3/(eta*kappa) 计算各黏度；统一使用 32×16 单元的试算网格、100 Myr 结束时间及 10 Myr 输出间隔，并说明这是粗网格教学试算，尚未按真实地球标定或完成收敛验证。生成三个独立可编辑 PRM，检查语法和初始场，然后提交三个有时间上限的短程运行。只比较实际完成的温度、速度和热流输出；若尚未演化到可比阶段，明确说明，不称已达到稳态。
```

English:

```text
Build three 2D Boussinesq thermal-convection models in a 1000 × 500 km box, starting from the installed ASPECT 3.1.0 convection-box cookbook. Use free-slip velocity on all four sides, insulating sidewalls, fixed top/bottom temperatures of 273/1573 K, and the same conductive initial profile plus a small identical perturbation. Target Ra = 10^2, 10^4, 10^5 by changing only viscosity. Use teaching values rho=3300 kg/m^3, alpha=3e-5 K^-1, Cp=1250 J/(kg K), k=4.125 W/(m K), g=9.81 m/s^2, so kappa=1e-6 m^2/s. Calculate each viscosity from Ra = rho*g*alpha*DeltaT*H^3/(eta*kappa). Use the same 32 × 16 cell pilot mesh, 100 Myr end time and 10 Myr output interval; label this as a coarse teaching run, not an Earth-calibrated or converged result. Create three separate editable PRMs, check syntax and preview initial fields, then submit three bounded pilot runs. Compare only completed temperature, velocity and heat-flux outputs; if they have not reached a comparable evolved state, say so rather than claiming steady convection.
```

## ASPECT 2 · 660 km 相变与冷板片 / Slab and phase transition

中文：

```text
我想测试冷板片代理是否穿过 660 km 相变界面。先检索已安装 ASPECT 3.1.0 的完整算例，确认使用内置相变物理、不依赖外部 shared library。建立延伸到 660 km 以下的二维模型，两组使用相同的倾斜冷板片代理和被动示踪场，仅比较零与非零相变密度跃变；几何、黏度、温度和边界条件保持一致。记录相变律、Clapeyron 斜率、密度跃变及单位。生成两份可编辑 PRM 并检查；仅当当前运行环境支持完整物理时提交有时间上限的短程试算，按实际示踪场报告最大深度随时间变化。若参考算例只是含相变的对流，或短程试算还没到 660 km，请标成机制示意，不声称已经证明板片穿透或滞留。
```

English:

```text
I want to test whether a cold slab analogue crosses a 660 km phase boundary in ASPECT 3.1.0. First find a complete installed example that uses built-in phase physics without an external shared library. Set up a 2D domain extending below 660 km, the same cold dipping slab analogue and passive slab tracer in both cases, and compare zero versus nonzero phase density jump while holding geometry, viscosity, temperatures and boundaries fixed. Record the phase law, Clapeyron slope, density jump and units. Create two editable PRMs, validate them and run bounded pilots only if the installed runtime supports the complete physics. Report actual tracer maximum depth versus time. If the reference is merely convection with a phase transition, or the pilots never reach 660 km, label it as a mechanism illustration and do not claim slab penetration or lower-mantle trapping.
```

## ASPECT 3 · 层析成像转初始场 / Tomography to initial field

中文：

```text
请把我上传的层析成像图转换成 ASPECT 初始条件候选。先识别图中的物理量、绝对值还是异常值、坐标与深度方向、色标端点和单位；缺什么就逐项问我。必须由我提供或认可波速到密度的转换关系及参考密度，不能从颜色唯一反演密度。完成标定后再数字化，展示所得初始密度图和来源记录，接入兼容的 ASPECT 模型且不要偷偷改流变；接入有效时再检查输入并做有时间上限的短程试算。请区分标定的初始场与真正的地球物理反演。
```

English:

```text
Use the tomography image I upload to build an ASPECT initial-condition candidate. Identify the plotted quantity, whether values are absolute or anomalies, coordinates, depth direction, colorbar limits and units. Ask for any missing calibration and for an explicit seismic-velocity-to-density conversion with reference density; do not infer density uniquely from colors. Digitize only after I provide or approve those values, show the derived density map and provenance, connect it to a compatible model without silently changing rheology, then check the input and run a bounded pilot if the coupling is valid. Distinguish the calibrated initial field from a geophysical inversion.
```

## ASPECT 4 · 论文三维地幔柱 / 3D plume from a paper

中文：

```text
请只使用我上传论文中的三维地幔柱主模型。逐项提取几何、热化学异常、状态方程、流变、相变、边界条件、初始温度和密度，注明 PDF 页码与原单位，列出所有缺失值。随后用已安装 ASPECT 3.1.0 的内置插件建立三维物理类比模型，先采用适合短程试算的网格；展示初始温度、参考黏度和密度剖面，记录论文数值到输入值的每一步换算及缺失过程。检查完整 PRM，只有有效时才提交有时间上限的启动试算。实际演化结果出现前不要称已经复现论文或地幔柱已上升，也不要只为了画面好看改参数。
```

English:

```text
Use only the main 3D plume model in the paper I upload. Extract its geometry, thermochemical anomaly, equations of state, rheology, phase changes, boundary conditions, initial temperatures and density, with PDF pages and original units; list every missing value. Then make an ASPECT 3.1.0 3D analogue using installed plugins and a modest pilot mesh. Show initial temperature, reference viscosity and density sections, record every paper-to-input conversion and each missing process. Validate the complete PRM and submit only a short bounded startup run if it is valid. Do not call this a reproduction or claim a rising plume until actual evolved output supports it; do not tune parameters merely for a prettier image.
```

## I2VIS 1 · 密度差与瑞利–泰勒不稳定 / Density contrast

中文：

```text
请用内置 I2VIS rayleigh_taylor 教学模板做两组密度差对比。先按匹配源码的参数说明核对 rock/2/markro 和 rock/3/markro 的含义；保持上层较重，几何、黏度、温度、边界条件、网格和输出计划相同。材料 2 的参考密度保持 3300 kg/m^3，材料 3 分别取 3400 和 3500 kg/m^3，在相同参考温度下比较 100 与 200 kg/m^3 的参考密度差，保留热膨胀公式。生成两组 init.t3c 与 mode.t3c，检查后提交两个有时间上限的短程运行。展示初始密度、温度、参考黏度图，只比较实际完成的 HDF5 输出；所有模板值标明是教学假设，不是观测值。
```

English:

```text
Use the bundled rayleigh_taylor I2VIS teaching template for a two-case density-contrast comparison. Read the exact source-linked meanings of rock/2/markro and rock/3/markro; keep the heavier upper layer, geometry, viscosity, temperature, boundaries, grid and output schedule fixed. Keep material 2 reference density at 3300 kg/m^3 and compare material 3 reference densities of 3400 and 3500 kg/m^3, giving contrasts of 100 and 200 kg/m^3 at the same reference temperature. Retain the thermal-expansion law. Generate both init.t3c and mode.t3c, validate them and submit two bounded short runs. Show the initial density/temperature/reference-viscosity previews and compare only actual completed HDF5 outputs. Label all template values as teaching assumptions, not measurements.
```

## I2VIS 2 · 初始热异常与地幔柱 / Mantle plume

中文：

```text
请从内置 I2VIS mantle_plume 教学模板出发，按匹配的源码说明笛卡尔深度方向、初始热异常、材料密度、热膨胀和参考黏度；保留模板材料编号与边界条件。生成可编辑的 init.t3c 和 mode.t3c，展示初始温度、密度和对数参考黏度图，然后提交一次有时间上限的短程运行。报告真实完成状态和 HDF5 文件；若短程结果尚未显示热柱上升，就说明这是初始条件与启动演示。
```

English:

```text
Start from the bundled I2VIS mantle_plume teaching template. Explain its Cartesian depth direction, initial hot anomaly, material densities, thermal expansion and reference viscosities using the matched source. Preserve the template material IDs and boundaries. Create an editable init.t3c/mode.t3c pair, show initial temperature, density and logarithmic reference-viscosity previews, then submit one bounded short run. Report the actual completion state and HDF5 files; if the short run does not yet show plume ascent, say it is an initial-condition and startup demonstration.
```
