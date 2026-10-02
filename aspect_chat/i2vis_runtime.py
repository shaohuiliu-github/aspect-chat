"""Trusted runtime entry. Exit zero from upstream is not sufficient proof of success."""
from pathlib import Path
import json,os,subprocess,sys
from . import i2vis

def main():
    phase=sys.argv[1];root=Path(sys.argv[2]).resolve();out=root/'output';info=i2vis.validate_files((out/'init.t3c').read_text(),(out/'mode.t3c').read_text())
    if not info['ok']:raise ValueError('; '.join(info['errors']))
    tables=root/'Phases'
    if not tables.exists():tables.symlink_to(i2vis.source_root()/'Phases',target_is_directory=True)
    # Upstream BCPush.c calls fclose(NULL) if its optional file is absent.
    # An explicit disabled file preserves the intended no-pushing default.
    if not (out/'pushing.t3c').exists():(out/'pushing.t3c').write_text('0-addPushing\n')
    import h5py,numpy as np
    if phase=='initialize':
        checkpoint=out/info['parameters']['init/output'];checkpoint.unlink(missing_ok=True)
        (out/'file.t3c').write_text('0\n')
        code=subprocess.call([str(i2vis.runtime_root()/'bin/in2h5')],cwd=out)
        if code or not checkpoint.is_file():raise ValueError('I2VIS initialization failed or did not create the expected HDF5 checkpoint')
        with h5py.File(checkpoint,'r+') as h:
            for name in ('Nodes/tk','Nodes/ro','Nodes/cp','Nodes/kt','Particles/Position','Material/Properties'):
                if name not in h or not np.isfinite(h[name][...]).all():raise ValueError('Invalid checkpoint dataset '+name)
            for name in ('Nodes/tk','Nodes/ro','Nodes/cp','Nodes/kt'):
                if (h[name][...]<=0).any():raise ValueError('Nonpositive initial '+name+'; check material IDs, coverage and marker count')
            coupling=out/'image-coupling.json'
            if coupling.exists():
                spec=json.loads(coupling.read_text())
                if spec['method']!='thermal_anomaly':raise ValueError('Unsupported I2VIS tomography coupling')
                from .initial_fields import ascii_field
                positions=h['Particles/Position'][...];ids=h['Particles/markt'][...];material=spec['material_id'];selected=(ids==material)
                if not selected.any():raise ValueError('Tomography material has no markers')
                props=h['Material/Properties'][material];rho0,alpha,compressibility=props[17:20]
                if alpha<=0:raise ValueError('Thermal density coupling needs positive thermal expansivity')
                x,y=positions[selected,0],positions[selected,1]
                target=ascii_field(out,'image-density.dat',x,y)
                # EOS inversion at the explicit reference pressure; retain rock identity/rheology.
                temperature=298.15+(1-target/(rho0*(1+compressibility*(spec['pressure_bar']-1)*1e-3)))/alpha
                if (temperature<=0).any() or (temperature>5000).any():raise ValueError('Tomography inversion gives implausible temperature (outside 0..5000 K)')
                markk=h['Particles/markk'][...];markk[selected]=temperature;h['Particles/markk'][...]=markk
                gx=h['Nodes/gx'][...];gy=h['Nodes/gy'][...];xx,yy=np.meshgrid(gx,gy,indexing='ij');tk=h['Nodes/tk'][...]
                # Apply to nodes dominated by this material, so other layers retain their initialization.
                from scipy.spatial import cKDTree
                _,nearest=cKDTree(positions).query(np.column_stack((xx.ravel(),yy.ravel())))
                mask=(ids[nearest]==material);target=ascii_field(out,'image-density.dat',xx.ravel()[mask],yy.ravel()[mask])
                tk[mask]=298.15+(1-target/(rho0*(1+compressibility*(spec['pressure_bar']-1)*1e-3)))/alpha;h['Nodes/tk'][...]=tk
                spec['applied_markers']=int(selected.sum());(out/'image-coupling-applied.json').write_text(json.dumps(spec,indent=2))
        if (out/'image-coupling.json').exists():
            code=subprocess.call([str(i2vis.runtime_root()/'bin/recouple')],cwd=out)
            if code:raise ValueError('Coupled material initialization failed')
            with h5py.File(checkpoint) as h:
                for name in ('Nodes/tk','Nodes/ro','Nodes/cp','Nodes/kt','Nodes/nu'):
                    if not np.isfinite(h[name][...]).all() or (h[name][...]<=0).any():raise ValueError('Invalid coupled '+name)
        print('chatGFD initialization verified: '+checkpoint.name,flush=True)
    elif phase=='solve':
        outputs=i2vis.parse_mode((out/'mode.t3c').read_text())['outputs']
        for row in outputs:(out/(row[0]+'.h5')).unlink(missing_ok=True)
        (out/'file.t3c').write_text('0\n')
        code=subprocess.call([str(i2vis.runtime_root()/'bin/i2h5')],cwd=out)
        if code:raise ValueError('I2VIS exited '+str(code))
        expected=out/(outputs[-1][0]+'.h5')
        if not expected.exists():raise ValueError('I2VIS stopped before the final configured checkpoint; inspect the log')
        with h5py.File(expected) as h:
            for name in ('Nodes/ro','Nodes/tk','Nodes/cp','Nodes/kt','Nodes/Velocity'):
                if name not in h or not np.isfinite(h[name][...]).all():raise ValueError('Nonfinite or missing '+name)
            for name in ('Nodes/ro','Nodes/tk','Nodes/cp','Nodes/kt'):
                if (h[name][...]<=0).any():raise ValueError('Nonpositive '+name+' in the final checkpoint')
        print('chatGFD simulation verified: '+expected.name,flush=True)
    else:raise ValueError('Unknown runtime phase')

if __name__=='__main__':
    try:main()
    except Exception as e:print('chatGFD ERROR: '+str(e),flush=True);raise SystemExit(1)
