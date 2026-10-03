# chatGFD 2.0.4

Install and start Docker. On Mac, open Terminal, type `bash ` (with the space), drag this folder's `start.sh` into Terminal, and press Return. On Windows, double-click `Start.bat` (Linux containers); on Linux, run `bash start.sh` here. Open the displayed local URL, enter your API key in Settings, choose ASPECT or I2VIS at the upper left, and select your conversation model below the composer.

The Mac package no longer contains an unsigned `.command` shortcut. The first launch downloads the container image; wait for the local URL. Repeat the same Terminal step to start later. To stop, type `bash `, drag the same `start.sh` into Terminal, then type ` stop` and press Return. Closing Terminal does not stop the container. Files remain in `workspace`.

PDF, image and parameter uploads belong in the composer. Generated files can be edited and run again manually without a conversation API call. Simulation state and errors appear in chat; logs expand beneath each task. Results stay in `workspace/runs`. On Mac/Linux, stop with `bash start.sh stop`; on Windows, double-click `Stop.bat`.

Initial diagrams use independent input evaluation; they do not launch a solver. Unsupported inputs are reported. Reference viscosity is not nonlinear effective viscosity. Paper reproduction prioritizes physical parameter evidence (PDF page, units, conversions, assumptions) before numerical convergence. See LICENSE-NOTICES.md and the validation report for the installed I2VIS variant and portable backend.
