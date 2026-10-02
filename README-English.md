# chatGFD

**Test your Earth science ideas with simulations. See what is physically possible.**

Geophysical Fluid Dynamics Simulation

[中文](README.md) · [Copy installation commands](INSTALL.md) · [Releases and validation report](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v2.0.0)

A local conversational workspace for ASPECT and i2vis, for geology, geochemistry, seismology and paleomagnetism research, with a first-model guide for beginners. The Docker image bundles solvers, Python dependencies and versioned offline references. No GitHub ZIP or separate solver installation is required.

## Start

Install and start Docker, then copy the commands in the [installation guide](INSTALL.md). Open the local webpage, enter your API key in Settings, select ASPECT or i2vis at the upper left, and choose the chat model below the composer. Outputs stay in your own workspace for ParaView and other software.

## Workflow

Upload PDF, image, PRM or i2vis inputs in the composer. Sent attachments remain visible in chat. New workspaces default to English; language switching and conversation deletion preserve model/result files.

Paper modeling prioritizes physical alignment: original values and units, PDF pages, supporting excerpts, conversions, actual input values, assumptions and missing items. Evidence is tied to the input revision and copied into run snapshots. Syntax validity is not paper reproduction. Discretization and nonlinear convergence must then be assessed separately.

Independent code draws initial temperature, density and reference viscosity directly from supported input functions and material parameters. It never launches a simulator for a preview. Unsupported features are reported. Reference viscosity is not nonlinear effective viscosity.

Image conversion needs a calibrated legend, coordinates, units and an explicit physical relationship. A simple ASPECT material can use a density-composition proxy. The installed i2vis variant can convert a thermal density anomaly into initial temperature for a specified rock and reference pressure; this changes temperature-dependent rheology. Seismic velocity alone does not uniquely determine density.

Parameter errors and colored simulation states appear directly in chat. Edit, check and run files manually without a conversation API call, and expand actual logs. Sweeps use independent snapshots with core and time budgets.

## Knowledge and runtime

ASPECT is the verified 3.1.0 release, with all 1,796 stable PRM files, manuals, API documentation, parameter entries, World Builder and tools. Development and Wiki navigation records are opt-in references.

The installed i2vis is the user-supplied Gerya/Yang/Faccenda HDF5 variant, pinned to a203df002bf8e41c3a29ad0c4857cef3d1daf0a1. It includes corresponding source, phase tables, source-linked parameter entries and three short teaching templates. The portable linear backend substitutes SuiteSparse UMFPACK for Intel MKL and checks backward error. This does not certify scientific equivalence with MKL. Arbitrary I2VIS branches are not drop-in runtime inputs.

Reference-only sources include [I2ELVIS planet](https://github.com/FormingWorlds/i2elvis_planet) and [Gou/Liu paper settings](https://github.com/YirenGou/Gou-and-Liu-2026-Dripping-Tectonics). Select these explicitly, then align their physics and input format before adaptation. See [knowledge provenance](knowledge-manifest.json).

## Source and scope

Application: AGPL-3.0-or-later. Independent solver/reference licenses remain distinct; see [notices](packaging/LICENSE-NOTICES.md). The user confirmed local i2vis redistribution permission; documentary evidence is still pending.

Complete corresponding source/build context is in the Release source ZIP and in the image under /opt/aspect-chat and /opt/chatgfd-adapter. From the source ZIP's source directory: `docker build -f packaging/Dockerfile -t chatgfd-local .`.

Keys, conversations and results stay in your workspace; cloud chat requires internet and your API quota. Scientific review remains necessary. Short smoke runs do not replace mesh convergence or research benchmarks. Plain Docker writes normal host files; the optional launcher also enables host Open Folder actions.
