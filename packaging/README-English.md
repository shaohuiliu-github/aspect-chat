# ASPECT Chat 1.1.1

Online launchers pull the published multi-platform image on first launch. Offline bundles import a matching local image. Registry publication must be verified before distributing an online launcher.

# ASPECT Chat portable package

Install and start Docker Desktop (Linux containers on Windows), extract the package, and run Start.command on macOS, Start.bat on Windows, or `bash start.sh` on Linux. ASPECT, MPI, Python, official v3.1.0 source/examples/manuals and parameter knowledge are already bundled. Enter your own API key in Settings and choose a model in the conversation header.

The universal ZIP includes both images and selects the architecture automatically. For smaller packages, Apple Silicon uses arm64; Intel Macs and typical Windows/Linux PCs use amd64. Cloud conversations still require internet and API credits; no language-model weights are included. The release contains an empty workspace and never includes the author's API keys or models.

Files persist in `workspace/`: current drafts in `cases/<id>/draft.prm`, inputs in `cases/<id>/assets/`, results in `runs/<id>/output/`, and logs in each run directory. Open outputs directly in ParaView or other software. Keep the launcher window open for the UI's Open Folder buttons. Closing the browser or launcher leaves calculations running. Use Stop.command, Stop.bat or `bash start.sh stop` to stop the container safely; active jobs are marked interrupted and files remain.

PDF/image/PRM uploads are supported. For models with relative WB/ASCII files, upload a ZIP containing the model folder with a unique entry named model.prm or input.prm, or copy the whole folder into workspace/inputs and import the entry PRM's host path from the model panel. Arbitrary external host folders are not mounted.

The upstream image tagged v3.1.0 was found to contain a 3.2.0-pre executable. This package rebuilds the actual v3.1.0 source tag and verifies its binary version. Version-matched runtime parameter declarations are included in the read-only knowledge base. The source and Docker build recipe are under source/. See 验证报告.json for the checks actually performed; no native Windows validation is implied by Linux amd64 emulation checks.

World Builder is enabled; FastScape is disabled. Custom compiled plugins must target the image's Linux architecture and ASPECT/deal.II versions; macOS dylib and Windows dll files cannot be loaded by the Linux solver.

For updates or relocation, stop first and preserve your workspace. To share the app with others, share the original ZIP, not a used workspace. The launcher listens only on localhost and automatically chooses another port if 8517 is occupied.

Knowledge now includes all 1,796 stable PRM files, 293 manual pages, 1,159 API pages, 1,696 individually indexed parameter declarations, contribution scripts/notebook source, input dependency records, and World Builder 1.1.1 schema. Development and Wiki navigation sources are explicitly marked reference-only and excluded from default retrieval. Corresponding application and ASPECT source is inside the image under /opt/aspect-chat.
