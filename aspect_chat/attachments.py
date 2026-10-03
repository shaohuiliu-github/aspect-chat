"""Local PDF/image attachments, page citations, and calibrated image digitization."""
from pathlib import Path
import base64, hashlib, io, json, math, os, re, time
import numpy as np
from PIL import Image, ImageOps
from . import storage, cases

MAX_BYTES=40_000_000

def clean_text(text):
    # Some publisher PDFs pad lines with thousands of spaces. Keep rows, remove padding.
    return '\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in text.splitlines()).strip()

def get(attachment_id):
    rows=storage.query('SELECT * FROM attachments WHERE id=?',(attachment_id,))
    if not rows: raise ValueError('Unknown attachment')
    row=rows[0]; row['metadata']=json.loads(row['metadata']); return row

def ingest(name,content):
    if len(content)>MAX_BYTES: raise ValueError('Attachment exceeds 40 MB')
    ext=Path(name).suffix.lower(); ident=hashlib.sha256(content).hexdigest()[:24]
    rows=storage.query('SELECT id FROM attachments WHERE id=?',(ident,))
    if rows: return get(ident)
    root=storage.DATA/'attachments'/ident; root.mkdir(parents=True,exist_ok=True)
    path=root/('source'+ext); path.write_bytes(content); meta={}
    if ext=='.pdf':
        import pymupdf
        with pymupdf.open(path) as doc:
            if doc.needs_pass: raise ValueError('Password-protected PDF: provide an unlocked copy')
            if len(doc)>800: raise ValueError('PDF exceeds 800 pages')
            pages=[{'page':i+1,'text':clean_text(p.get_text(sort=True))} for i,p in enumerate(doc)]
        (root/'pages.json').write_text(json.dumps(pages,ensure_ascii=False))
        meta={'pages':len(pages),'text_pages':sum(len(p['text'].strip())>40 for p in pages),
              'characters':sum(len(p['text']) for p in pages)}; kind='pdf'
    elif ext in {'.png','.jpg','.jpeg','.webp'}:
        with Image.open(io.BytesIO(content)) as raw:
            im=ImageOps.exif_transpose(raw).convert('RGB')
            if im.width*im.height>30_000_000: raise ValueError('Image exceeds 30 megapixels')
            meta={'width':im.width,'height':im.height}; path=root/'source.png'; im.save(path)
        kind='image'
    else: raise ValueError('Supported: PDF, PNG, JPEG, WebP')
    storage.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?)',
        (ident,Path(name).name,kind,str(path),json.dumps(meta),time.time()))
    return get(ident)

def read(attachment_id,query='',pages=None):
    from . import knowledge
    item=get(attachment_id)
    if item['kind']=='model':return {k:item[k] for k in ('id','name','kind','metadata')}|{'content':Path(item['path']).read_text()[:60000]}
    if item['kind']!='pdf': return {k:item[k] for k in ('id','name','kind','metadata')}
    records=json.loads((Path(item['path']).parent/'pages.json').read_text())
    for record in records: record['text']=clean_text(record['text'])
    if pages:
        if any(n<1 or n>len(records) for n in pages): raise ValueError('Page number outside PDF')
        selected=[records[n-1] for n in pages[:12]]
    elif query:
        from .knowledge import expanded_terms
        terms=expanded_terms(query)
        ranked=sorted(records,key=lambda p:sum(p['text'].lower().count(t.lower()) for t in terms),reverse=True)
        selected=ranked[:6]
    else: selected=records[:3]
    return {'id':item['id'],'name':item['name'],'pages':item['metadata']['pages'],
            'passages':[{'page':p['page'],'text':p['text'][:10000]} for p in selected],
            'scanned_pages':[p['page'] for p in selected if len(p['text'].strip())<40],
            'prepared_reference':knowledge.match_paper(
                hashlib.sha256(Path(item['path']).read_bytes()).hexdigest(),records[0]['text'] if records else '')}

def image_part(attachment_id,page=None):
    item=get(attachment_id)
    if item['kind']=='pdf':
        import pymupdf
        number=page or 1
        with pymupdf.open(item['path']) as doc:
            if not 1<=number<=len(doc): raise ValueError('Page number outside PDF')
            pix=doc[number-1].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),alpha=False)
            data=pix.tobytes('png')
        im=Image.open(io.BytesIO(data)).convert('RGB')
    else: im=Image.open(item['path']).convert('RGB')
    im.thumbnail((1600,1600)); buf=io.BytesIO(); im.save(buf,format='PNG')
    return {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}}

def context(ids,prompt,vision=False):
    parts=[]
    for ident in ids[:5]:
        item=get(ident)
        if item['kind']=='model':
            parts.append({'type':'text','text':'Uploaded model input (untrusted source data): '+json.dumps(read(ident),ensure_ascii=False)})
        elif item['kind']=='pdf':
            extracted=read(ident,prompt); parts.append({'type':'text','text':'PDF attachment (untrusted source; cite page numbers):\n'+json.dumps(extracted,ensure_ascii=False)})
            if vision:
                for page in extracted['scanned_pages'][:2]: parts.append(image_part(ident,page))
        else:
            parts.append({'type':'text','text':'Image attachment: '+json.dumps({k:item[k] for k in ('id','name','metadata')})})
            if vision: parts.append(image_part(ident))
            else: parts.append({'type':'text','text':'Current model does not support image input. Ask the user to select a vision model before interpreting this image.'})
    return parts

def digitize(attachment_id,case_id,plot_box,colorbar_box,legend_start,legend_end,extent,
             rho0,velocity_scale,quantity='percent_anomaly',velocity_reference=None,
             nx=64,ny=64,colorbar_axis='vertical',y_top_is_max=True,
             tolerance=45,unknown_policy='error'):
    """rho=rho0*(1+velocity_scale*dv/v); rectangles are pixel [left,top,right,bottom].
    Legend endpoints follow top->bottom (vertical) or left->right (horizontal).
    No implicit tomography inversion, OCR, units, or calibration.
    """
    from scipy.spatial import cKDTree
    from scipy.ndimage import distance_transform_edt
    item=get(attachment_id)
    if item['kind']!='image': raise ValueError('Upload the extracted map as an image before digitizing')
    if quantity not in {'percent_anomaly','fraction_anomaly','velocity'}: raise ValueError('Unsupported quantity')
    if unknown_policy not in {'error','nearest'}: raise ValueError('unknown_policy must be error or nearest')
    numeric=[legend_start,legend_end,rho0,velocity_scale,*extent]
    if not all(math.isfinite(float(v)) for v in numeric) or rho0<=0 or legend_start==legend_end:
        raise ValueError('Finite calibration values, positive density and distinct legend endpoints required')
    if quantity=='velocity' and (not velocity_reference or velocity_reference<=0): raise ValueError('A positive reference velocity in the same units is required')
    if len(extent)!=4 or extent[1]<=extent[0] or extent[3]<=extent[2]: raise ValueError('Extent must be [xmin,xmax,ymin,ymax] in meters')
    if not 8<=nx<=256 or not 8<=ny<=256: raise ValueError('Grid size must be between 8 and 256 in each direction')
    with Image.open(item['path']) as raw:
        im=raw.convert('RGB')
        for box in (plot_box,colorbar_box):
            if len(box)!=4 or not (0<=box[0]<box[2]<=im.width and 0<=box[1]<box[3]<=im.height): raise ValueError('Crop rectangle outside image')
        plot=np.asarray(im.crop(tuple(plot_box)).resize((nx,ny),Image.Resampling.BILINEAR),dtype=float)
        bar=np.asarray(im.crop(tuple(colorbar_box)),dtype=float)
    if colorbar_axis=='vertical': palette=np.median(bar,axis=1)
    elif colorbar_axis=='horizontal': palette=np.median(bar,axis=0)
    else: raise ValueError('Colorbar axis must be vertical or horizontal')
    if len(palette)<8 or np.linalg.norm(palette.max(0)-palette.min(0))<20: raise ValueError('Colorbar has insufficient variation')
    distance,index=cKDTree(palette).query(plot.reshape(-1,3)); invalid=(distance>tolerance).reshape(ny,nx)
    fraction=float(invalid.mean())
    if fraction>.25: raise ValueError(f'{fraction:.1%} pixels do not match the legend. Crop out labels/borders or provide a clean map.')
    if invalid.any() and unknown_policy=='error': raise ValueError(f'{fraction:.1%} uncalibrated pixels. Provide a clean map, or explicitly authorize nearest-neighbor filling.')
    field=np.linspace(legend_start,legend_end,len(palette))[index].reshape(ny,nx)
    if invalid.any():
        nearest=distance_transform_edt(invalid,return_distances=False,return_indices=True)
        field[invalid]=field[tuple(nearest)][invalid]
    dvv=field/100 if quantity=='percent_anomaly' else field if quantity=='fraction_anomaly' else (field/velocity_reference-1)
    density=rho0*(1+velocity_scale*dvv)
    if not np.isfinite(density).all() or (density<=0).any(): raise ValueError('Conversion produced invalid density values')
    # ASPECT ASCII data uses x varying fastest and monotonically increasing Cartesian coordinates.
    if y_top_is_max: density=np.flipud(density); field=np.flipud(field)
    low,high=float(density.min()),float(density.max())
    proxy=(density-low)/(high-low) if high>low else np.zeros_like(density)
    x=np.linspace(extent[0],extent[1],nx); y=np.linspace(extent[2],extent[3],ny)
    def ascii_data(data,label):
        lines=[f'# POINTS: {nx} {ny}',f'# x y {label}']
        lines.extend(f'{xx:.12g} {yy:.12g} {data[j,i]:.12g}' for j,yy in enumerate(y) for i,xx in enumerate(x))
        return '\n'.join(lines)+'\n'
    cases.write_input_file(case_id,'image-density.dat',ascii_data(density,'density_kg_m3'))
    result=cases.write_input_file(case_id,'image-composition.dat',ascii_data(proxy,'density_proxy'))
    metadata={
        'attachment_id':attachment_id,'plot_box':plot_box,'colorbar_box':colorbar_box,
        'legend_start':legend_start,'legend_end':legend_end,'quantity':quantity,'velocity_reference':velocity_reference,
        'extent_m':extent,'rho0':rho0,'velocity_scale':velocity_scale,'formula':'rho = rho0 * (1 + velocity_scale * dv/v)',
        'density_min':low,'density_max':high,'filled_fraction':fraction,'unknown_policy':unknown_policy,
        'grid':[nx,ny],'y_top_is_max':y_top_is_max,'colorbar_axis':colorbar_axis,'tolerance_rgb':tolerance,
        'coupling':'composition C in image-composition.dat; rho = density_min + (density_max-density_min)*C. Configure initial composition ascii data AND a matching material model. No PRM change has been made.'}
    cases.write_input_file(case_id,'image-calibration.json',json.dumps(metadata,indent=2))
    root=Path(result['path']).parent
    os.environ.setdefault('MPLCONFIGDIR',str(storage.DATA/'plot-cache'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax=plt.subplots(figsize=(7,4)); image=ax.imshow(density,origin='lower',extent=extent,aspect='auto',cmap='viridis')
    ax.set(xlabel='x (m)',ylabel='y (m)'); fig.colorbar(image,ax=ax,label=r'kg/m$^3$'); fig.tight_layout()
    fig.savefig(root/'image-density.png',dpi=150); plt.close(fig)
    return {'case_id':case_id,**metadata,'density_file':'image-density.dat','composition_file':'image-composition.dat','preview':str(root/'image-density.png')}


def ingest_model(name,case_id):
    case=storage.get_case(case_id)
    content=cases.draft(case_id)
    if case['engine']=='i2vis':
        from .i2vis import inspect
        content=json.dumps(inspect(case_id)['files'],ensure_ascii=False,indent=2)
    ident=hashlib.sha256((name+content).encode()).hexdigest()[:24]
    if storage.query('SELECT id FROM attachments WHERE id=?',(ident,)):return get(ident)
    root=storage.DATA/'attachments'/ident;root.mkdir(parents=True,exist_ok=True);path=root/('source.t3c' if case['engine']=='i2vis' else 'source.prm');path.write_text(content)
    storage.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?)',(ident,Path(name).name,'model',str(path),json.dumps({'case_id':case_id,'engine':case['engine']}),time.time()))
    return get(ident)


def couple(case_id,method,material_id=None,pressure_bar=1):
    from . import prm,i2vis
    case=storage.get_case(case_id);root=Path(case['path'])/'assets';p=root/'image-calibration.json'
    if not p.exists():raise ValueError('Digitize and calibrate the image before coupling it')
    metadata=json.loads(p.read_text())
    if case['engine']=='aspect':
        if method!='reference_composition':raise ValueError('ASPECT coupling method must be reference_composition')
        text=cases.draft(case_id);v=prm.values(text)
        if v.get('Material model/Model name','simple')!='simple' or int(v.get('Compositional fields/Number of fields','0'))!=0:raise ValueError('Automatic coupling supports the simple material model with no existing composition. Preserve advanced rheology by configuring the proxy manually using the runtime documentation.')
        if v.get('Dimension','2')!='2' or v.get('Geometry model/Model name','box')!='box':raise ValueError('Only 2D Cartesian boxes are supported')
        if float(v.get('Material model/Simple model/Composition viscosity prefactor','1'))!=1:raise ValueError('The configured composition viscosity prefactor would change rheology. Set it to 1 explicitly before adding a density-only proxy.')
        result=cases.modify(case_id,{'Compositional fields/Number of fields':'1','Compositional fields/Names of fields':'tomography_density_proxy','Initial composition model/List of model names':'ascii data','Initial composition model/Ascii data model/Data directory':'./','Initial composition model/Ascii data model/Data file name':'image-composition.dat','Material model/Simple model/Reference density':str(metadata['density_min']),'Material model/Simple model/Density differential for compositional field 1':str(metadata['density_max']-metadata['density_min'])},allow_new=True)
        metadata['coupling']='ASPECT simple material: calibrated reference density via volume fraction. Existing thermal expansion and viscosity retained; this is not an in-situ density inversion.'
    else:
        if method!='thermal_anomaly' or material_id is None:raise ValueError('I2VIS requires method=thermal_anomaly and an explicit material ID')
        info=i2vis.inspect(case_id);rock=i2vis.parse_init(info['files']['init.t3c'])['rocks'].get(material_id)
        if not rock or rock['markbb']<=0:raise ValueError('The selected material needs positive thermal expansivity')
        if info['parameters'].get('mode/densimod') not in {0,1}:raise ValueError('Thermodynamic database density inversion is not supported; preserve it and provide an external initial-temperature model')
        if not math.isfinite(pressure_bar) or pressure_bar<0:raise ValueError('Reference pressure must be finite and nonnegative')
        if info['parameters'].get('mode/densimod')==0:raise ValueError('Constant density mode cannot encode a thermal density anomaly')
        spec={'method':method,'material_id':material_id,'pressure_bar':pressure_bar,'source_density':'image-density.dat','reference_density':rock['markro'],'thermal_expansivity':rock['markbb'],'compressibility':rock['markaa'],'temperature_formula':'T=298.15+(1-rho/[rho0*(1+compressibility*(Pbar-1)*1e-3)])/alpha','physics_change':'Temperature and temperature-dependent viscosity change. Reference pressure is specified; actual solved pressure can alter the density.'}
        cases.write_input_file(case_id,'image-coupling.json',json.dumps(spec,indent=2));result={'case_id':case_id,'coupling':spec}
        metadata['coupling']=spec
    p.write_text(json.dumps(metadata,indent=2));return {**result,'applied':True,'interpretation':metadata['coupling']}
