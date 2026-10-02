# Distribution notices

The bundled ASPECT release is provided by the Computational Infrastructure for Geodynamics:
https://github.com/geodynamics/aspect/tree/v3.1.0
https://hub.docker.com/r/geodynamics/aspect

ASPECT is licensed under GPL version 2 or later. Its complete official v3.1.0 source tree and original license notices are included under source/knowledge/sources/aspect-3.1.0/ in offline/source packages and /opt/aspect-chat/knowledge/sources/aspect-3.1.0/ inside the image. Third-party notices included in that tree remain intact. The immutable upstream image contains deal.II, OpenMPI, Trilinos, p4est and other dependencies; their package copyright files are retained under /usr/share/doc in the image. PyMuPDF is distributed under the GNU Affero General Public License (or a commercial license); this distribution uses its AGPL release. Other Python dependency licenses remain in their installed dist-info directories.

This ASPECT Chat application's Python and web code, container supervisor and launchers are distributed under GNU Affero General Public License version 3 or later. See source/LICENSE-AGPL-3.0.txt for the complete terms. Corresponding application source and Docker build recipe accompany this package. Modified builds must preserve the applicable source and licensing obligations. This package carries no upstream endorsement.

The GPL-licensed ASPECT executable is an independent subprocess, exchanging parameter and result files with the application. The original ASPECT licensing and source availability obligations continue to apply to the distributed executable and any changes to it.

Source archives for dependencies can be obtained using their official distributions:
https://pypi.org/project/PyMuPDF/1.26.7/#files
https://www.dealii.org/
https://www.open-mpi.org/
https://github.com/geodynamics/aspect/tree/v3.1.0/contrib/docker

No API keys, personal conversations, uploaded papers or user model outputs are included in the original release package.

Official API text is generated from the same ASPECT release. Development snapshot source retains the upstream ASPECT license. Wiki entries contain navigation links and headings rather than redistributed article bodies. World Builder source, licenses and generated parameter definitions are included. The image contains all corresponding application source and the complete build recipe under /opt/aspect-chat; these can be exported with docker cp.
