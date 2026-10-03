# chatGFD: start in four steps

1. Install and open [Docker Desktop](https://www.docker.com/products/docker-desktop/). Wait until it is running.
2. On Mac, press **⌘ + Space**, search for **Terminal**, and open it. Type `bash ` (with a trailing space), drag this folder's **start.sh** into Terminal, and press Return. On Windows, double-click **Start.bat**. On Linux, run `bash start.sh` in this folder.
3. The first launch downloads the environment. Wait for the address shown in Terminal, then open it in your browser.
4. Click **Settings** at the lower left, enter your API key, and save. Describe your model in the chat box and send.

**Next time:** Open Docker Desktop and repeat step 2. No need to download the launcher again.

**Results:** This folder's `workspace/runs`. Upload papers, images or parameter files using the upload button in chat.

**Stop:** On Mac, type `bash ` in Terminal, drag in the same `start.sh`, type ` stop`, and press Return. On Windows, double-click `Stop.bat`. Closing Terminal does not stop the container.
