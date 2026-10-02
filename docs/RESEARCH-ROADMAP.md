# Research directions / 科研扩展计划

Implemented: versioned ASPECT/I2VIS adapters, paper evidence ledger, calibrated image conversion, bounded direct initial diagrams, local job snapshots, manual editing and parameter sweeps. These features create candidate experiments, not a certificate of paper reproduction.

目前已实现：版本匹配的双求解器、论文物理参数来源记录、标定图片转换、限定范围的独立初始图、本地运行快照、手动编辑与参数扫描。它们用于建立可核查的候选实验，不能自动证明论文已复现。

## Next priorities / 后续优先级

1. **Physics specification / 物理规格表**: solver-neutral units, constitutive equations, coordinate/sign conventions and assumption IDs; map to each code only after equivalence checks. 跨代码复现必须先对齐方程、单位与材料模型。
2. **Observation comparison / 观测对比**: compare predicted uplift, surface velocity and gravity at observed coordinates/times, with uncertainty and explicit conversion models. 对比地质抬升、GPS 速度和重力；层析波速需要另有矿物物理关系。
3. **Thermal/material histories / 热与物质历史**: export particle P–T–t paths, tracer provenance and melting histories for thermochronology and geochemistry. 为热年代学与地球化学提供有单位和坐标的轨迹。
4. **Rotation histories / 旋转历史**: integrate particle trajectories and vorticity into block-rotation comparisons for paleomagnetism; this is not a geodynamo or magnetic-field solver. 古地磁可对比地块旋转；磁场生成属于另一类求解器。
5. **Uncertainty and convergence / 不确定性与收敛**: vary uncertain physics first, then test grid, timestep and solver tolerance on agreed observables. 先测试物理假设，再对同一观测量检查数值收敛。
6. **Reproduction archive / 复现归档**: paper DOI and permitted inputs, assumption ledger, dataset checksums, image digest, code revision, core budget, outputs and validation notes in an exportable bundle. 让论文对应一份可审阅的实验归档，补全镜像摘要、测试条件与来源授权。

These are proposed extensions, not current UI controls or completed scientific validation. 以上为规划，不是现有按钮或已完成的科研认证。
