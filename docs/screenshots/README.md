# Demo image provenance / 演示图来源

These five images were selected from the chatGFD demo recorded on 3 October 2026. UI screenshots show the application as recorded; language-model selections and task histories are illustrative and can differ in your workspace. No API key is shown. Results are coarse demonstrations, not validated research benchmarks.

这五张图选自 2026 年 10 月 3 日录制的 chatGFD 演示。界面图保留录制时的应用状态，语言模型选择和任务历史仅用于展示，不含 API 密钥。结果为粗分辨率演示，不代表已通过科研基准或收敛验证。

| File | Source and meaning |
| --- | --- |
| `chatgfd-model-identity.png` | Recorded “What model are you?” conversation; distinguishes the selected language model from the ASPECT runtime. |
| `chatgfd-preview-and-tasks.png` | Recorded initial-temperature preview and actual task states, with edit and rerun controls. |
| `tomography-to-density.png` | Original uploaded section and density grid actually used as input. The section was redrawn from `LLNL_model_cropped_cratons_faults.txt.gz` in the ASPECT 3.1.0 `tomography_based_plate_motions` cookbook, approximately 30°N, 130–170°E, 300–1300 km depth. The constant factor 0.3 is an explicit teaching assumption, not the cookbook's depth-dependent conversion. |
| `aspect-rayleigh-comparison.png` | Actual ASPECT outputs from the three Ra runs, shown in ParaView at 100 Myr. Same thermal setup; viscosities differ. |
| `i2vis-hot-anomaly-evolution.png` | Actual saved i2vis temperature at 2 Myr, with full and zoomed views. Dashed cyan is the initial 1700 K contour; solid white is the current contour. |

Tomography references: [ASPECT 3.1.0 cookbook](https://aspect-documentation.readthedocs.io/en/v3.1.0/user/cookbooks/cookbooks/tomography_based_plate_motions/doc/tomography_based_plate_motions.html), [Simmons et al. (2019), LLNL-G3D-JPS](https://doi.org/10.1093/gji/ggz102). The image is a redrawn data section, not a reproduced paper figure. A rectangular teaching mapping does not replace spherical geometry, and seismic velocity alone does not uniquely determine density.

[Watch the demo](https://youtu.be/BNjAN6mV1Xs) · [中文 README](../../README.md) · [English README](../../README-English.md)
