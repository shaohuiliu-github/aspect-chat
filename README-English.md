# chatGFD

**Build geodynamic models through conversation. Test Earth science ideas and learn numerical modeling.**

Geophysical Fluid Dynamics Simulation

[中文](README.md) · [Installation guide](INSTALL.md) · [Releases and review report](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5)

chatGFD turns a description into editable, runnable ASPECT / i2vis models. Researchers in geology, geochemistry, seismology and paleomagnetism can build comparisons to test the physical feasibility of a hypothesis. Beginners can start with a simple example, build a model faster, and learn how materials, boundaries and parameter changes affect the simulation.

Docker bundles the solvers, Python environment and offline knowledge base. No GitHub source download or separate solver installation is needed.

## Start from Terminal

Install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/). On Mac / Linux, copy:

```sh
mkdir -p "$HOME/chatgfd-workspace"
docker run -d --pull=always --name chatgfd --restart unless-stopped \
  --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 \
  --mount "type=bind,source=$HOME/chatgfd-workspace,target=/workspace" \
  -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" \
  ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

Open [http://127.0.0.1:8517](http://127.0.0.1:8517) and enter your API key in **Settings** at the lower left. The first launch downloads the environment. Models and results stay in `chatgfd-workspace` under your home directory, ready for ParaView or other software.

Use `docker start chatgfd` later and `docker stop chatgfd` to stop. For an existing install, use the start command. See [installation instructions](INSTALL.md) for upgrades, port conflicts and Windows PowerShell.

For buttons that open Finder / Explorer directly, use the small [launcher](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.5/chatGFD-2.0.5-online.zip). On Mac, extract it, type `bash ` in Terminal, drag in `start.sh`, and press Return. Windows uses Start.bat.

## Research and education

- **Test hypotheses:** Upload a paper or image, align the physics, units, sources and missing inputs, then create models and compare parameters. Simulation helps assess physical feasibility.
- **Learn modeling:** Click First model or Model examples and start with a short description. The assistant explains key settings in chat. Ask to halve the viscosity or edit inputs without running to learn through small changes.

[Six short example prompts](DEMO_CASES.md) are copy-ready and available from the homepage. Paper and tomography cases need uploads. Teaching defaults are explained in chat and can be changed later.

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
