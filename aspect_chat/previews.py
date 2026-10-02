"""One cached initial-state ASPECT evaluation, never evolution plots."""
from pathlib import Path
import hashlib, json, os, time
from . import storage, cases, prm

FIELDS={'density':('density',r'kg/m$^3$'),'viscosity':('viscosity','Pa s'),'temperature':('T','K')}

def signature(case_id):
    params=prm.values(cases.draft(case_id))
    # Changing duration, log/output settings or solver controls does not change initial fields.
    ignored={'End time','Output directory','Resume computation','Nonlinear solver scheme','Max nonlinear iterations',
             'Nonlinear solver tolerance','CFL number','Maximum first time step','Maximum time step','Maximum relative increase in time step'}
    initial={k:v for k,v in params.items() if k not in ignored and not k.startswith(('Postprocess/','Termination criteria/','Checkpointing/','Solver parameters/'))}
    h=hashlib.sha256(b'initial-preview-v3'+json.dumps(initial,sort_keys=True).encode()); root=Path(storage.get_case(case_id)['path'])/'assets'
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in {'.wb','.txt','.dat','.csv','.json'}:
            h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()

def schedule(case_id):
    sig=signature(case_id)
    rows=storage.query('SELECT job_id FROM previews WHERE case_id=? AND signature=?',(case_id,sig))
    if rows: return rows[0]['job_id']
    # A lightweight separate snapshot: same geometry/material/initial functions and inputs;
    # capped mesh, no advection/Stokes solve, initial material response with zero initial velocity.
    text=cases.draft(case_id); vals=prm.values(text)
    changes={
        'End time':vals.get('Start time','0'),
        'Resume computation':'false','Nonlinear solver scheme':'no Advection, no Stokes',
        'Mesh refinement/Initial global refinement':str(min(3,int(vals.get('Mesh refinement/Initial global refinement','2')))),
        'Mesh refinement/Initial adaptive refinement':'0',
        'Mesh deformation/Mesh deformation boundary indicators':'',
        'Mesh deformation/Additional tangential mesh velocity boundary indicators':'',
        'Postprocess/List of postprocessors':'visualization',
        'Postprocess/Visualization/Output format':'vtu',
        'Postprocess/Visualization/Number of grouped files':'0',
        'Postprocess/Visualization/List of output variables':'material properties',
        'Postprocess/Visualization/Material properties/List of material properties':'density,viscosity',
        'Postprocess/Visualization/Time between graphical output':'0',
        'Termination criteria/Termination criteria':'end time',
    }
    text=prm.patch(text,changes,allow_new=True)
    job=cases.enqueue(case_id,cores=1,kind='preview',text_override=text,timeout=min(180,int(storage.config()['timeout_seconds'])))
    storage.execute('INSERT OR IGNORE INTO previews VALUES(?,?,?,?)',(case_id,sig,job['job_id'],time.time()))
    return job['job_id']

def latest(case_id):
    rows=storage.query('SELECT p.job_id,j.state,j.note FROM previews p JOIN jobs j ON j.id=p.job_id WHERE p.case_id=? ORDER BY p.created DESC LIMIT 1',(case_id,))
    if not rows: return None
    r=rows[0]; root=storage.DATA/'runs'/r['job_id']/'initial-fields'
    r['files']={k:str(root/(k+'.png')) for k in FIELDS if (root/(k+'.png')).exists()}
    if (root/'metadata.json').exists(): r['metadata']=json.loads((root/'metadata.json').read_text())
    return r

def render(job_id):
    import meshio,numpy as np
    os.environ.setdefault('MPLCONFIGDIR',str(storage.DATA/'plot-cache'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt,tri,colors
    root=storage.DATA/'runs'/job_id; files=sorted((root/'output').rglob('solution-00000*.vtu'))
    if not files: raise ValueError('ASPECT did not write an initial VTU solution')
    points=[]; fields={k:[] for k in FIELDS}
    for path in files:
        mesh=meshio.read(path); points.append(mesh.points)
        for key,(name,unit) in FIELDS.items():
            if name not in mesh.point_data: raise ValueError('Initial VTU does not contain '+name)
            fields[key].append(np.asarray(mesh.point_data[name]).reshape(-1))
    points=np.concatenate(points); data={k:np.concatenate(v) for k,v in fields.items()}
    vals=prm.values((root/'input.prm').read_text()); dimension=int(vals.get('Dimension','2'))
    # 3D is a point slab around the central Cartesian z coordinate, not a volume inversion.
    section=None; keep=np.ones(len(points),dtype=bool)
    if dimension==3:
        z=points[:,2]; section=float((z.max()+z.min())/2); distances=np.abs(z-section)
        threshold=float(np.quantile(distances,.15)); keep=distances<=max(threshold,1e-12)
    xy=points[keep,:2]; xy,first=np.unique(xy,axis=0,return_index=True)
    if len(xy)<3: raise ValueError('Insufficient points to show initial field')
    triangulation=tri.Triangulation(xy[:,0],xy[:,1])
    # Avoid filling holes or gaps in annulus/chunk geometry with artificial triangles.
    triangles=xy[triangulation.triangles]; edges=np.linalg.norm(triangles-np.roll(triangles,1,axis=1),axis=2)
    cutoff=np.median(edges.max(1))*3
    triangulation.set_mask(edges.max(1)>cutoff)
    target=root/'initial-fields'; target.mkdir(exist_ok=True); ranges={}
    for key,(_,unit) in FIELDS.items():
        v=data[key][keep][first]
        if not np.isfinite(v).all(): raise ValueError('Nonfinite initial '+key+' values; inspect ASPECT material response')
        ranges[key]={'min':float(v.min()),'max':float(v.max()),'unit':unit}
        norm=colors.LogNorm(vmin=v.min(),vmax=v.max()) if key=='viscosity' and v.min()>0 and v.max()/v.min()>10 else None
        fig,ax=plt.subplots(figsize=(6,4))
        # Flat fields still have a readable color bar.
        image=ax.tripcolor(triangulation,v,shading='gouraud',cmap='magma' if key=='temperature' else 'viridis',norm=norm)
        ax.set(xlabel='x (m)',ylabel='y (m)',aspect='equal'); fig.colorbar(image,ax=ax,label=unit)
        fig.tight_layout(); fig.savefig(target/(key+'.png'),dpi=160); plt.close(fig)
    metadata={'ranges':ranges,'dimension':dimension,'z_slab_center_m':section,
        'source':'ASPECT initial VTU, no time evolution, no Stokes solve',
        'global_refinement':vals['Mesh refinement/Initial global refinement'],
        'limitations':'Initial pressure/composition/temperature are initialized by ASPECT. Viscosity uses the initial zero velocity/strain rate. Adaptive refinement and mesh deformation are disabled; global refinement is capped at 3. 3D uses a central Cartesian z slab.'}
    (target/'metadata.json').write_text(json.dumps(metadata,indent=2)); return metadata
