# 简短案例提示词 / Simple model prompts

先选择 ASPECT 或 i2vis，点击首页「经典模型示例」即可填入。论文和层析图案例先上传附件。教学默认值、缺失参数与下一步修改建议由助手在对话中说明。

Choose ASPECT or i2vis and click Model examples to insert a prompt. Upload the paper or tomography image first when needed. The assistant explains teaching defaults, missing information and suggested edits in chat.

## ASPECT 1 · 三组 Ra 对流 / Three Rayleigh numbers

中文：

```text
建立一个 1000×500 km 的二维地幔对流模型，速度边界自由滑移，顶底温度固定。比较 Ra=100、10000、100000，生成参数文件并运行，简单说明关键设置。
```

English:

```text
Build a 1000 × 500 km 2D mantle-convection model with free-slip boundaries and fixed top and bottom temperatures. Compare Ra = 100, 10,000 and 100,000; generate the inputs, run the models and briefly explain the settings.
```

## ASPECT 2 · 相变与俯冲 / Phase transition and subduction

中文：

```text
建立二维俯冲模型，比较有、无 660 km 相变时板片能否进入下地幔。生成两组参数文件，说明关键设置后运行。
```

English:

```text
Build a 2D subduction model to compare whether a slab enters the lower mantle with and without the 660 km phase transition. Create two input files and explain the key settings before running.
```

## ASPECT 3 · 层析图转初始场 / Tomography to initial field

中文：

```text
把我上传的层析图转换为初始密度场，建立一个 ASPECT 模型。先告诉我需要补充哪些信息，再生成参数文件和初始场。
```

English:

```text
Turn my uploaded tomography image into an initial density field for an ASPECT model. Tell me what information is missing, then generate the inputs and show the initial field.
```

## ASPECT 4 · 论文三维地幔柱 / 3D plume from a paper

中文：

```text
根据我上传的论文，用 ASPECT 建立三维地幔柱主模型。提取关键参数并注明页码和单位，告诉我缺什么，生成参数文件和初始场。
```

English:

```text
Use ASPECT to build the main 3D mantle-plume model from my uploaded paper. Extract the key parameters with page numbers and units, tell me what is missing, and generate the inputs and initial fields.
```

## I2VIS 1 · 密度差与滴落 / Density contrast and dripping

中文：

```text
建立两组岩石圈滴落模型，参考密度差分别为 100 和 200 kg/m³，其他设置相同。生成参数文件，运行并比较演化。
```

English:

```text
Build two lithospheric-dripping models with reference density contrasts of 100 and 200 kg/m³, keeping other settings the same. Generate the inputs, run both models and compare the evolution.
```

## I2VIS 2 · 热异常与地幔柱 / Thermal anomaly and plume

中文：

```text
建立一个地幔柱模型，看看底部附近的热异常如何上升。生成参数文件和初始场，运行并简单解释设置。
```

English:

```text
Build a mantle-plume model to explore how a hot anomaly near the base rises. Generate the inputs and initial fields, run the model and briefly explain the settings.
```

想继续修改，可直接说「把黏度降低一半」「延长计算时间」或「先别运行，只修改参数」。论文数值与教学假设会区分记录；运行是否完成以任务状态为准。

To change a model, try “halve the viscosity”, “extend the simulation time”, or “edit the inputs without running”. Paper values and teaching assumptions are recorded separately; task status shows actual completion.
