# chatGFD

**Build models through conversation. Explore Earth science ideas with simulations.**

Geophysical Fluid Dynamics Simulation

[中文](README.md) · [Watch the 4-minute demo](https://youtu.be/BNjAN6mV1Xs) · [Installation guide](INSTALL.md) · [Downloads and releases](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5)

Make your Earth science ideas easier to model, teach and discuss. **chatGFD is an early demo product** for building and exploring simple geodynamic models through conversation, using **ASPECT and i2vis**. Describe an idea, inspect the inputs and initial fields, change a parameter, and see how the model evolves.

The chat assistant helps organize inputs and explain the setup; real geodynamic solvers perform the numerical calculation. Input files remain editable, and results stay on your computer for viewing in ParaView or other tools.

### “What model are you?”

This demo conversation identifies the selected language model and the actual simulation engine. The language model handles the conversation; ASPECT / i2vis performs the numerical calculation.

![chatGFD answering What model are you, identifying the language model and ASPECT simulation engine](docs/screenshots/chatgfd-model-identity.png)

## Why this matters

- **Earth science education:** Help teachers and students explore buoyancy, viscosity, temperature and boundary conditions through small numerical experiments. Make abstract processes visible and ask what assumptions produce a particular result.
- **Connections across Earth science:** Give researchers in geology, geochemistry, seismology, paleomagnetism and related fields a practical starting point for discussing physical mechanisms. Use a conceptual sketch, paper or calibrated image to guide an initial model whose assumptions can be inspected and revised together.
- **A first step into geodynamics:** Build a first working model faster and learn how geometry, material properties, initial fields and boundary conditions fit together. Continue learning by editing the inputs.
- **Early exploration of geological hypotheses:** Turn a proposed mechanism into a simple experiment, compare alternative assumptions and explore physical plausibility within the model's stated limits.
- **A starting point for experienced geodynamicists:** Establish initial geometry, fields and input files for a new idea, then refine the physics, resolution and implementation using your usual research workflow.

The aim is to make the first modeling step more accessible, support teaching and collaboration, and leave scientific assumptions open to inspection.

**Current limits:** Knowledge-base coverage and the author's available development time are limited. The product currently supports simple models and is not yet well suited to complex research models. Physical alignment comes first: values, units, material laws, boundary conditions, missing inputs and assumptions need careful review. Mesh and solver convergence must then be assessed before scientific conclusions are drawn. A successful run alone does not establish that a geological hypothesis is correct or that a published model has been reproduced.

Docker bundles the solvers, Python environment and offline knowledge base. No GitHub source download or separate solver installation is needed.

## First time: four steps

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), open it, and wait until it is running.
2. On Mac, press **⌘ + Space**, search for **Terminal**, and open it. Copy the entire block below into Terminal and press Return. The first download takes time; wait until the command prompt returns.

```sh
mkdir -p "$HOME/chatgfd-workspace"
docker run -d --pull=always --name chatgfd --restart unless-stopped \
  --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 \
  --mount "type=bind,source=$HOME/chatgfd-workspace,target=/workspace" \
  -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" \
  ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

3. Open **[http://127.0.0.1:8517](http://127.0.0.1:8517)** in your browser.
4. Click **Settings** at the lower left, enter your API key, and save. Type the model you want in the chat box and send.

**No repository download or separate ASPECT, i2vis or Python installation is needed.** The commands also work on Linux. [Windows instructions](INSTALL.md#windows-english).

## Open it next time

Open Docker Desktop, then copy this into Terminal:

```sh
docker start chatgfd
```

Open **[http://127.0.0.1:8517](http://127.0.0.1:8517)**. Do not repeat the first-time installation block.

Models and results are saved in **`chatgfd-workspace`** inside your home folder. To stop, enter `docker stop chatgfd` in Terminal.

## From conversation to results

**1. Inspect initial fields, edit inputs and follow task status.** Temperature, density and reference-viscosity previews are evaluated directly from supported input settings. The task panel shows time-based names, success or failure, output-folder access and logs. Use **Edit parameters**, then **Run again** to try a change.

![ASPECT initial temperature preview, editing and rerun controls, and actual success and failure states](docs/screenshots/chatgfd-preview-and-tasks.png)

**2. Turn a tomography image into model input and compare it with the original.** Coordinates, a color legend, units and the physical mapping must be explicit. This example preserves the source colors for comparison and uses a teaching density proxy, not a unique inversion from seismic velocity. The image was redrawn from LLNL-G3D-JPS data in an ASPECT cookbook; see [image provenance](docs/screenshots/README.md).

![Original tomography image beside converted reference density, using the same colors and an explicit teaching conversion](docs/screenshots/tomography-to-density.png)

**3. ASPECT: compare three Rayleigh numbers.** The same 2D thermal setup uses different viscosities to change Ra. These are actual solver outputs displayed in ParaView. Open the saved `solution.pvd` to play the evolution; the coarse demonstrations do not establish convergence.

![Actual ASPECT temperature outputs for 2D mantle convection at Rayleigh numbers 1e4, 1e5 and 1e6](docs/screenshots/aspect-rayleigh-comparison.png)

**4. i2vis: inspect early hot-anomaly evolution.** Actual saved i2vis outputs show the full model, a zoomed view, and initial versus current temperature contours. See the [full demo](https://youtu.be/BNjAN6mV1Xs) for animation, density comparisons and ParaView operation.

![Actual i2vis output at 2 Myr, showing the full model, zoom and initial versus current 1700 K contours](docs/screenshots/i2vis-hot-anomaly-evolution.png)

[Six short example prompts](DEMO_CASES.md) are copy-ready and available from the homepage. Paper and tomography cases need uploads. Teaching defaults are explained in chat and can be changed later.

The demo video is edited to shorten waiting times. Some saved replies are replayed progressively; evolution frames come from actual solver outputs. The paper example is an explicitly simplified 2D teaching approximation.

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

## Acknowledgments and related projects

Special thanks to **Professor Taras Gerya** for his support of this project. Thanks also to the ASPECT and i2vis developers and the geodynamics community.

- [ASPECT website](https://aspect.geodynamics.org/) · [ASPECT source](https://github.com/geodynamics/aspect)
- [i2vis method: Gerya & Yuen (2003)](https://doi.org/10.1016/j.pepi.2003.09.006)
- [Public I2ELVIS planet reference code](https://github.com/FormingWorlds/i2elvis_planet): a different branch from this demo's i2vis runtime.
