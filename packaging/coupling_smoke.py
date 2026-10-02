"""Actual image coupling checks in an isolated running container workspace."""
from pathlib import Path
import json,time
import numpy as np,h5py
from aspect_chat import storage,cases,i2vis,attachments,initial_fields,runner
storage.save_config({'task_cores':1,'max_total_cores':2,'timeout_seconds':180})
model='''set Dimension = 2
set Use years instead of seconds = true
set End time = 1000
subsection Geometry model
 set Model name = box
 subsection Box
  set X extent = 1000000
  set Y extent = 500000
 end
end
subsection Initial temperature model
 set List of model names = function
 subsection Function
  set Function expression = 300+1300*(1-y/500000)
 end
end
subsection Material model
 set Model name = simple
 subsection Simple model
  set Reference density = 3300
  set Thermal expansion coefficient = 0
  set Viscosity = 1e21
 end
end
subsection Gravity model
 set Model name = vertical
end
subsection Boundary velocity model
 set Zero velocity boundary indicators = left, right, top, bottom
end
subsection Boundary temperature model
 set Fixed temperature boundary indicators = bottom, top
 set List of model names = box
 subsection Box
  set Bottom temperature = 1600
  set Top temperature = 300
 end
end
subsection Postprocess
 set List of postprocessors = visualization
end
subsection Mesh refinement
 set Initial global refinement = 2
 set Initial adaptive refinement = 0
end
'''
a=cases.create('coupled-aspect',model)['case_id'];cases.write_input_file(a,'image-density.dat','# POINTS: 2 2\n0 0 3300\n1000000 0 3350\n0 500000 3300\n1000000 500000 3350\n');cases.write_input_file(a,'image-composition.dat','# POINTS: 2 2\n0 0 0\n1000000 0 1\n0 500000 0\n1000000 500000 1\n');cases.write_input_file(a,'image-calibration.json',json.dumps({'density_min':3300,'density_max':3350}));attachments.couple(a,'reference_composition');job_a=cases.enqueue(a)['job_id']
t=i2vis.templates('rayleigh_taylor');b=i2vis.create('coupled-i2vis',t['init.t3c'],t['mode.t3c'])['case_id'];cases.write_input_file(b,'image-density.dat','# POINTS: 2 2\n0 0 3250\n1000000 0 3250\n0 500000 3250\n1000000 500000 3250\n');cases.write_input_file(b,'image-calibration.json',json.dumps({'density_min':3250,'density_max':3250}));attachments.couple(b,'thermal_anomaly',material_id=2,pressure_bar=1)
_,_,fields,_,_,_=initial_fields.i2vis(storage.get_case(b));assert np.allclose(fields['density'][-1],3250) and not np.allclose(fields['density'][0],3250)
job_b=i2vis.enqueue(b)['job_id'];deadline=time.time()+200
while time.time()<deadline:
 states=[runner.status(j) for j in (job_a,job_b)]
 if all(s['state'] in runner.TERMINAL for s in states):break
 time.sleep(.5)
assert all(s['state']=='succeeded' for s in states),[(s['state'],s['log'][-4000:],s['validation_log'][-3000:]) for s in states]
root=storage.DATA/'runs'/job_b;applied=json.loads((root/'output/image-coupling-applied.json').read_text());assert applied['applied_markers']>0
with h5py.File(root/'output/initial.h5') as h:
 ids=h['Particles/markt'][...];temp=h['Particles/markk'][...];assert np.allclose(temp[ids==2],298.15+(1-3250/3300)/3e-5,atol=.01)
 rho=h['Nodes/ro'][...].reshape(len(h['Nodes/gx']),len(h['Nodes/gy']));assert np.isclose(rho[len(rho)//2,-4],3250,atol=1)
assert 'coupled material fields rebuilt' in states[1]['validation_log']
report={'aspect_job':job_a,'i2vis_job':job_b,'actual_initial_hdf5_density':True,'unselected_material_preserved_in_preview':True,'all_succeeded':True}
(storage.DATA/'coupling-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
