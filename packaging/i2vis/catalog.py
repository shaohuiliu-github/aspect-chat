"""Build source-linked I2VIS knowledge without importing anyone's workspace."""
from pathlib import Path
import hashlib,json,re,sys
root=Path(sys.argv[1]);manual=Path(sys.argv[2]);manual.mkdir(parents=True,exist_ok=True)
from aspect_chat import i2vis
units={'xsize':'m','ysize':'m','radius':'m','pinit':'Pa','GXKOEF':'m/s²','GYKOEF':'m/s²','timesum':'years','markn0':'Pa s','markn1':'Pa s','markro':'kg/m³','markbb':'1/K','markaa':'1/kbar','markcp':'J/(kg K)','markkt':'W/(m K)','markht':'W/m³; k-prefixed input is W/kg and is multiplied by reference density','markdh':'J/mol in the Arrhenius branch; sign may select a different law','markdv':'J/(mol bar) in the Arrhenius branch; special values select other branches','marka0':'Pa','marka1':'Pa','markb0':'dimensionless','markb1':'dimensionless','marke0':'strain','marke1':'strain','timebond':'years','maxtmstep':'years','vyfluid':'m/s','vymelt':'m/s','waterlev':'m','nubeg':'Pa s','nuend':'Pa s','nucontrast':'dimensionless'}
meanings={'cartpolar':'1: Cartesian, 2: 2D annulus. Cartesian y is depth downward.','marknu':'Rheology coefficient. Its meaning and units depend on markdh, markdv, markss and markmm; it is NOT generally the ASPECT strain-rate prefactor A. Read markslabomp.c viscosity branches.','markdh':'Activation term; negative and zero values are mode switches in several source branches, not simply negative activation energy.','markdv':'Pressure/activation-volume term. mpb in rheology is in bar. Some very large values select depth-dependent rheology. Do not convert by label alone.','marka0':'Initial cohesion term in strength = A(strain)+B(strain)*P*lamb.','markb0':'Initial friction coefficient B; not a friction angle in degrees.','densimod':'0: fixed rock reference density; 1: linear P/T density; >=2: thermodynamic phase tables (Perplex/MMA variant).','meltmod':'Switch for melting; material IDs also participate in hard-coded phase transformations.','markht':'Heat production per volume, except a k prefix requests mass-specific production multiplied by markro.','mnumx':'Initial markers per x cell. Marker injection and MRKNEW allocation can require more than minimal structural bounds; teaching models use 4×4.','printmod':'Log verbosity; not a physical control.'}
entry=manual/'entries';entry.mkdir(exist_ok=True)
source=(root/'in2fasth5.c').read_text();mode_source=(root/'loadh5.c').read_text()
a=i2vis.parse_init((root/'templates/subduction/init.t3c').read_text());b=i2vis.parse_mode((root/'templates/subduction/mode.t3c').read_text())
parameters={**a['parameters'],**b['parameters']}
for path,value in parameters.items():
 name=path.rsplit('/',1)[-1];ref='in2fasth5.c' if path.startswith(('init/','rock/')) else 'loadh5.c';body=(root/ref).read_text();match=re.search(re.escape(name)+r'\b',body);line=body[:match.start()].count('\n')+1 if match else 1
 scope=path if not path.startswith('rock/') else 'rock/<material_id>/'+name
 doc=f'# Parameter: {scope}\n\nSolver: I2VIS source revision {i2vis.REVISION}.\nSource: {ref}:{line}.\n\nUnits: {units.get(name,"Dimensionless/index or source-specific; inspect the linked source before converting.")}\n\nMeaning: {meanings.get(name,"Read the source and complete input template. Positional input order is binding; keep value labels when editing.")}\n\nExample value: {value} (supplied subduction template, NOT a universal default or paper value).\n'
 key=hashlib.sha256(scope.encode()).hexdigest()[:20];(entry/(key+'.md')).write_text(doc)
(manual/'overview.md').write_text(f'''# I2VIS modeling guide

This is the exact supplied Taras Gerya / Jianfeng Yang / Manuele Faccenda version, revision {i2vis.REVISION}. It supports Cartesian and annular domains; the direct preview currently supports Cartesian boxes. It uses C, finite differences and markers. Templates are teaching models, not paper reconstructions.

## Input files and outputs
init.t3c describes grid, markers, rocks, boundary equations, material boxes and initial temperature. mode.t3c describes checkpoint names, save blocks and general, surface, Stokes, thermal and hydration/melting controls. Inputs are positional; slash-prefixed TOKENS are comments, not arbitrary free text. Four ~ delimiters terminate rock, boundary, material-box and temperature sections. Use short relative HDF5 names: init output initial.h5, mode load initial h. Each save row is name, h, cycle count, maximum marker displacement, maximum temperature increment, maximum time step in years. file.t3c is managed as a fresh-run index by the runtime. Restarting external checkpoints is not supported by this interface yet.

The wrapper creates a disabled pushing.t3c if absent; the original optional-file branch calls fclose(NULL). The original scientific source is preserved. Outputs, input snapshots, backend and exact source revision remain on disk.

## Physics alignment before numerics
Record geometry, gravity, initial temperature, density conventions, composition/material IDs, thermal parameters, every flow-law convention and boundary conditions before changing grid resolution. I2VIS material IDs are not interchangeable labels: e.g. 9/10 transform at 1573 K and 0/1 participate in air/water/sedimentation. New teaching Rayleigh–Taylor models use material 2/3 and inactive surface processes. Existing subduction source retains its geological IDs.

Pressure inside creep routines is bar; P for brittle strength is converted to Pa. In the Arrhenius branch E is J/mol, V is J/(mol bar), so V_SI (m³/mol) = V_input / 1e5. Several sign/value branches change this convention: inspect the implementation first. The friction parameter is B in A+B P, not an ASPECT angle. Heat production k-prefixed values are W/kg; unprefixed values are W/m³. Mode time limits and save time steps are input in years and multiplied by SecYear. Cartesian y is positive downward.

## Constitutive equations
Read markslabomp.c's viscosity branches: simple Newtonian eta=marknu when E=V=0 and stress-independent; other laws include inverse-prefactor conventions, strain weakening, pressure, water, Peierls creep and depth-dependent activation enthalpy. Do not map marknu to ASPECT A by name. Linear density uses rho=markro*(1-markbb*(T-298.15))*(1+markaa*(Pbar-1)*1e-3). Thermodynamic-table density is a different model.

## Tomography coupling
Digitization needs user-approved coordinates, legend, units, reference velocity, reference density and velocity-density relation. I2VIS thermal_anomaly coupling uses the documented EOS inversion at an explicit reference pressure to change initial marker and nodal temperature for one material. Rock identity stays unchanged; temperature-dependent rheology changes. This is not a unique seismic inversion. Thermodynamic density mode is refused. ASPECT simple material coupling uses a reference-density composition proxy, with thermal expansion still active. All transformations have calibration JSON and immutable run snapshots.

## Portable numerical backend
The public runtime uses GCC/OpenMP/HDF5 and SuiteSparse UMFPACK. A checked adapter handles the source's one-based CSR nonsymmetric PARDISO call sequence. Every linear solve records backward error and rejects nonfinite or excessive values. This is not a certification of equivalence with Intel MKL. A teaching-model smoke test is not a mesh-convergence study. For a paper, compare benchmarks and convergence against the original source/backend separately, after physics alignment.

## Primary reference documentation
Maierová and Gerya (2024), I2VIS relamination model documentation: https://zenodo.org/records/14554728 . It describes another model/version; consult it for methods, not exact defaults of this variant. The PDF is linked rather than redistributed because its public record does not expose a clear license in the fetched metadata.
''')
(manual/'initial-fields.md').write_text('''# Direct initial-field diagrams

No simulator is launched to draw initial fields. Cartesian material boxes and temperature structures 0 and 4 (bilinear / half-space cooling) are evaluated directly from inputs. Density uses the explicit linear EOS at P=0 unless tomography is coupled at its stated pressure. Viscosity is a reference input coefficient bounded by markn0/markn1, not an effective strain-rate-dependent solution. Unsupported annular shapes, phase tables or other structures are reported, not guessed. The grid in in2fasth5.c is automatically nonuniform in y; the diagram is a geometric input check rather than a plot of the discretization.
''')
print('I2VIS parameter documents:',len(list(entry.glob('*.md'))))
