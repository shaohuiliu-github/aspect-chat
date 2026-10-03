# chatGFD

**Test your Earth science ideas with simulations. See what is physically possible.**

Geophysical Fluid Dynamics Simulation

[中文](README.md) · [Installation guide](INSTALL.md) · [Releases and validation report](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.3)

A local conversational workspace for ASPECT and i2vis, for geology, geochemistry, seismology and paleomagnetism research, with a first-model guide for beginners. The Docker image bundles solvers, Python dependencies and versioned offline references. No source checkout or separate solver installation is required.

## Start in four steps

1. Install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/).
2. Download the approximately 28 KB [chatGFD launcher](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.3/chatGFD-2.0.3-online.zip) and extract it.
3. Double-click `Start.command` on Mac or `Start.bat` on Windows. The first launch downloads the simulation environment and opens the webpage.
4. Enter your own model provider API key in **Settings** at the lower left. You can then chat and run models.

Models and results are saved in `chatGFD-2.0.3-online/workspace` inside the extracted folder, ready for ParaView and other software. The Docker image includes ASPECT, i2vis, Python dependencies and offline references. See the [installation guide](INSTALL.md) for command-line setup, Linux and upgrades.

If macOS cannot verify `Start.command` on first launch, follow the [installation guide](INSTALL.md) to use Apple's Open Anyway option in Privacy & Security.

## Workflow

Upload PDF, image, PRM or i2vis inputs in the composer. Sent attachments remain visible in chat. New workspaces default to English; language switching and conversation deletion preserve model/result files.

Paper modeling prioritizes physical alignment: original values and units, PDF pages, supporting excerpts, conversions, actual input values, assumptions and missing items. Evidence is tied to the input revision and copied into run snapshots. Syntax validity is not paper reproduction. Discretization and nonlinear convergence must then be assessed separately.

Independent code draws initial temperature, density and reference viscosity directly from supported input functions and material parameters. It never launches a simulator for a preview. Three-dimensional function boxes display an explicitly labeled central x-z section; strain fields are excluded from chemical material mixing. Unsupported features are reported. Reference viscosity is not nonlinear effective viscosity. Temperature uses blue/red, viscosity purple/yellow with a logarithmic scale, and density blue/green/yellow.

Image conversion needs a calibrated legend, coordinates, units and an explicit physical relationship. A simple ASPECT material can use a density-composition proxy. The installed i2vis variant can convert a thermal density anomaly into initial temperature for a specified rock and reference pressure; this changes temperature-dependent rheology. Seismic velocity alone does not uniquely determine density.

Parameter checks run in the background; missing inputs and errors appear in chat. Completion reminders and persistent task states make results visible. Edit and run again without a conversation API call, with minute-based task/output folder names and expandable logs. Sweeps use independent snapshots with core and time budgets.

## Knowledge and runtime

ASPECT is the verified 3.1.0 release, with all 1,796 stable PRM files, manuals, API documentation, parameter entries, World Builder and tools. Development and Wiki navigation records are opt-in references.

The installed i2vis is the user-supplied Gerya/Yang/Faccenda HDF5 variant, pinned to a203df002bf8e41c3a29ad0c4857cef3d1daf0a1. It includes corresponding source, phase tables, source-linked parameter entries and three short teaching templates. The portable linear backend substitutes SuiteSparse UMFPACK for Intel MKL and checks backward error. This does not certify scientific equivalence with MKL. Arbitrary I2VIS branches are not drop-in runtime inputs.

Reference-only sources include [I2ELVIS planet](https://github.com/FormingWorlds/i2elvis_planet) and [Gou/Liu paper settings](https://github.com/YirenGou/Gou-and-Liu-2026-Dripping-Tectonics). Select these explicitly, then align their physics and input format before adaptation. See [knowledge provenance](knowledge-manifest.json).

Uploaded papers can be analyzed locally with page, unit and assumption tracking. Personal paper notes are not distributed with the public source or image.

## Source and scope

Application: AGPL-3.0-or-later. Independent solver/reference licenses remain distinct; see [notices](packaging/LICENSE-NOTICES.md). The user confirmed local i2vis redistribution permission; documentary evidence is still pending.

Complete corresponding source/build context is in the Release source ZIP and in the image under /opt/aspect-chat and /opt/chatgfd-adapter. From the source ZIP's source directory: `docker build -f packaging/Dockerfile -t chatgfd-local .`.

Keys, conversations and results stay in your workspace; cloud chat requires internet and your API quota. Scientific review remains necessary. Short smoke runs do not replace mesh convergence or research benchmarks. Plain Docker writes normal host files; the optional launcher also enables host Open Folder actions.
