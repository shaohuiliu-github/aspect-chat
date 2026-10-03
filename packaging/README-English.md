# chatGFD 2.0.3

Install and start Docker. Open Start.command on macOS, Start.bat on Windows (Linux containers), or run bash start.sh on Linux. Open the displayed local URL, enter your API key in Settings, choose ASPECT or i2vis at the upper left, and select your conversation model below the composer.

If macOS says it cannot verify Start.command, try opening it once, then choose Open Anyway in System Settings → Privacy & Security. Only do this for a launcher you trust from the official chatGFD repository. You can instead run `bash start.sh` in Terminal from this folder. Apple instructions: https://support.apple.com/en-ie/102445

PDF, image and parameter uploads belong in the composer. Generated files can be edited and run again manually without a conversation API call. Simulation state and errors appear in chat; logs expand beneath each task. Results stay in workspace/runs. Stop with the matching Stop launcher.

Initial diagrams use independent input evaluation; they do not launch a solver. Unsupported inputs are reported. Reference viscosity is not nonlinear effective viscosity. Paper reproduction prioritizes physical parameter evidence (PDF page, units, conversions, assumptions) before numerical convergence. See LICENSE-NOTICES.md and the validation report for the installed I2VIS variant and portable backend.
