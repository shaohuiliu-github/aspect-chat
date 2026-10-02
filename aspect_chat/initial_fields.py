"""Pure input evaluation. Never launches ASPECT/I2VIS, never solves Stokes."""
import ast,math,operator,re
from pathlib import Path
import numpy as np
from scipy.special import erf,erfc
from scipy.interpolate import RegularGridInterpolator
from . import prm,storage

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow,ast.Mod:operator.mod}
CMP={ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Eq:operator.eq,ast.NotEq:operator.ne}
FUN={k:getattr(np,k) for k in ('sin','cos','tan','exp','sqrt','log','log10','abs','floor','ceil','arcsin','arccos','arctan','sinh','cosh','tanh')}
FUN.update(min=np.minimum,max=np.maximum,erf=erf,erfc=erfc,pow=np.power,atan2=np.arctan2)

def ternary(expr):
    expr=expr.strip()
    # Recursively rewrite parenthesized groups first, then the outer conditional.
    out='';i=0
    while i<len(expr):
        if expr[i]=='(':
            depth=1;j=i+1
            while j<len(expr) and depth:
                depth+= (expr[j]=='(')-(expr[j]==')');j+=1
            if depth:raise ValueError('Unbalanced function parentheses')
            out+='('+ternary(expr[i+1:j-1])+')';i=j
        else:out+=expr[i];i+=1
    depth=0;q=None;nested=0
    for i,c in enumerate(out):
        depth+=(c=='(')-(c==')')
        if depth:continue
        if c=='?':
            if q is None:q=i
            else:nested+=1
        elif c==':' and q is not None:
            if nested:nested-=1
            else:return 'where('+ternary(out[:q])+','+ternary(out[q+1:i])+','+ternary(out[i+1:])+')'
    return out

def evaluate(expr,variables):
    expr=ternary(expr).replace('^','**').replace('&&',' and ').replace('||',' or ')
    expr=re.sub(r'!(?!=)',' not ',expr).strip();tree=ast.parse(expr,mode='eval')
    if len(list(ast.walk(tree)))>800:raise ValueError('Function too complex for the direct preview')
    def walk(n):
        if isinstance(n,ast.Expression):return walk(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(float,int)):return n.value
        if isinstance(n,ast.Name) and n.id in variables:return variables[n.id]
        if isinstance(n,ast.BinOp) and type(n.op) in OPS:return OPS[type(n.op)](walk(n.left),walk(n.right))
        if isinstance(n,ast.UnaryOp):
            if isinstance(n.op,ast.USub):return -walk(n.operand)
            if isinstance(n.op,ast.UAdd):return walk(n.operand)
            if isinstance(n.op,ast.Not):return np.logical_not(walk(n.operand))
        if isinstance(n,ast.BoolOp):return (np.logical_and if isinstance(n.op,ast.And) else np.logical_or).reduce([walk(v) for v in n.values])
        if isinstance(n,ast.Compare):
            a=walk(n.left);answer=True
            for op,b in zip(n.ops,n.comparators):
                value=walk(b);answer=np.logical_and(answer,CMP[type(op)](a,value));a=value
            return answer
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and not n.keywords:
            args=[walk(a) for a in n.args]
            if n.func.id=='where' and len(args)==3:return np.where(*args)
            if n.func.id in FUN:return FUN[n.func.id](*args)
        raise ValueError('Unsupported function syntax: '+ast.dump(n)[:150])
    with np.errstate(all='ignore'):return walk(tree)

def function(vals,prefix,x,y,index=0):
    names=[n.strip() for n in vals.get(prefix+'/Variable names','x,y,t').split(',')]
    if vals.get(prefix+'/Coordinate system','cartesian')!='cartesian':raise ValueError('Direct function preview supports Cartesian coordinates only')
    variables={'pi':np.pi,'Pi':np.pi,'e':np.e,'t':0,'x':x,'y':y}
    for name,value in zip(names,(x,y,0)):variables[name]=value
    for item in vals.get(prefix+'/Function constants','').split(','):
        if item.strip():
            name,value=item.split('=',1);variables[name.strip()]=evaluate(value.strip(),variables)
    parts=vals.get(prefix+'/Function expression','').split(';')
    if index>=len(parts) or not parts[index].strip():raise ValueError('Missing initial function expression')
    return np.broadcast_to(evaluate(parts[index],variables),x.shape).copy()

def ascii_field(root,filename,x,y,column=2):
    p=(Path(root)/filename).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('ASCII preview data must be inside case assets')
    rows=np.loadtxt(p,comments='#');xx=np.unique(rows[:,0]);yy=np.unique(rows[:,1])
    if len(xx)*len(yy)!=len(rows):raise ValueError('ASCII input must be a complete Cartesian grid')
    values=rows[np.lexsort((rows[:,0],rows[:,1]))][:,column].reshape(len(yy),len(xx))
    interp=RegularGridInterpolator((yy,xx),values,bounds_error=True)
    return interp(np.stack((y.ravel(),x.ravel()),axis=-1)).reshape(x.shape)

def aspect(case):
    v=prm.values((Path(case['path'])/'draft.prm').read_text());fields={};errors={};notes=[]
    if v.get('Geometry model/Model name','box')!='box' or v.get('Dimension','2')!='2':raise ValueError('Direct preview currently supports 2D Cartesian boxes; no simulation was started')
    w=float(v.get('Geometry model/Box/X extent','1'));h=float(v.get('Geometry model/Box/Y extent','1'))
    origin=[float(v.get('Geometry model/Box/Box origin X coordinate','0')),float(v.get('Geometry model/Box/Box origin Y coordinate','0'))]
    x,y=np.meshgrid(np.linspace(origin[0],origin[0]+w,160),np.linspace(origin[1],origin[1]+h,100));assets=Path(case['path'])/'assets'
    def initial(prefix,index=0):
        model=v.get(prefix+'/List of model names') or v.get(prefix+'/Model name','function')
        if model=='function':return function(v,prefix+'/Function',x,y,index)
        if model=='ascii data':return ascii_field(assets,str(Path(v.get(prefix+'/Ascii data model/Data directory',''))/v.get(prefix+'/Ascii data model/Data file name','')),x,y,2+index)
        raise ValueError('Direct preview does not implement initial plugin '+model)
    try:fields['temperature']=initial('Initial temperature model')
    except Exception as e:errors['temperature']=str(e)
    n=int(v.get('Compositional fields/Number of fields','0'));weights=np.ones((1,*x.shape))
    try:
        if n:
            comp=np.stack([initial('Initial composition model',i) for i in range(n)]);rawcomp=comp.copy();comp=np.maximum(0,comp);total=comp.sum(axis=0);comp=comp/np.maximum(1,total)
            weights=np.concatenate((np.maximum(0,1-comp.sum(axis=0))[None,:,:],comp))
    except Exception as e:
        errors['density']=errors['viscosity']='Composition unavailable: '+str(e);weights=None
    material=v.get('Material model/Model name','simple')
    if material not in {'simple','visco plastic'}:errors['density']=errors['viscosity']='Direct material preview does not implement '+material;weights=None
    if weights is not None:
        sub='Simple model' if material=='simple' else 'Visco Plastic';base='Material model/'+sub+'/'
        def array(key,default):
            a=[float(s) for s in v.get(base+key,default).split(',')]
            if len(a)==1:a*=n+1
            if len(a)!=n+1:raise ValueError('Wrong material list length for '+key)
            return np.array(a)[:,None,None]
        try:
            rho=array('Reference density','3300') if material=='simple' else array('Densities','3300');alpha=array('Thermal expansion coefficient','2e-5') if material=='simple' else array('Thermal expansivities','3.5e-5')
            if 'temperature' not in fields:raise ValueError('Temperature is needed for thermally dependent density')
            tref=float(v.get(base+'Reference temperature','293'))
            fields['density']=(weights*rho*(1-alpha*(fields['temperature'][None,:,:]-tref))).sum(axis=0)
            if material=='simple' and n:fields['density']+=rawcomp[0]*float(v.get(base+'Density differential for compositional field 1','0'))
            notes.append('Density: volume-weighted reference densities with linear thermal expansion; pressure compressibility excluded. Reference temperature '+str(tref)+' K.')
        except Exception as e:errors['density']=str(e)
        try:
            if material=='simple':
                eta=array('Viscosity','5e24');beta=float(v.get(base+'Thermal viscosity exponent','0'));tref=float(v.get(base+'Reference temperature','293'))
                if beta:
                    if tref==0:raise ValueError('Nonzero thermal viscosity exponent with zero reference temperature')
                    eta=eta*np.clip(np.exp(-beta*(fields['temperature'][None,:,:]-tref)/tref),float(v.get(base+'Minimum thermal prefactor','1e-2')) or 0,float(v.get(base+'Maximum thermal prefactor','1e2')) or np.inf)
                fields['viscosity']=(weights*eta).sum(axis=0)
                if n:fields['viscosity']*=float(v.get(base+'Composition viscosity prefactor','1'))**rawcomp[0]
                notes.append('Simple-model viscosity from the configured reference and thermal exponent; no velocity field is solved.')
            else:
                # Explicit diagnostic strain rate and P=0. Do not invent a self-consistent viscosity.
                sr=float(v.get(base+'Reference strain rate','1e-15'));T=fields['temperature'][None,:,:]
                A=array('Prefactors for diffusion creep','1e-15');E=array('Activation energies for diffusion creep','0');grain=float(v.get(base+'Grain size','1e-3'));m=array('Grain size exponents for diffusion creep','0')
                diff=.5/A*grain**m*np.exp(np.minimum(E/(8.314*T),700))
                A=array('Prefactors for dislocation creep','5e-24');E=array('Activation energies for dislocation creep','0');power=array('Stress exponents for dislocation creep','1')
                dis=.5*A**(-1/power)*sr**((1-power)/power)*np.exp(np.minimum(E/(power*8.314*T),700))
                flow=v.get(base+'Viscous flow law','composite');eta=diff if flow=='diffusion' else dis if flow=='dislocation' else 1/(1/diff+1/dis)
                minimum=float(v.get(base+'Minimum viscosity','1e17'));maximum=float(v.get(base+'Maximum viscosity','1e28'));eta=np.clip(eta,minimum,maximum)
                fields['viscosity']=1/np.maximum((weights/eta).sum(axis=0),1e-300)
                notes.append(f'Reference creep viscosity: strain rate={sr:g} s^-1, P=0 Pa, harmonic mixing. Plastic yield, weakening, phase transitions, elasticity and Stokes coupling excluded; this is a reference map, not effective solver viscosity.')
        except Exception as e:errors['viscosity']=str(e)
    return x,y,fields,errors,notes,False

def i2vis(case):
    from . import i2vis as solver
    a=solver.parse_init((Path(case['path'])/'init.t3c').read_text());p=a['parameters']
    if p['init/cartpolar']!=1:raise ValueError('Direct I2VIS preview currently supports Cartesian models only')
    x,y=np.meshgrid(np.linspace(0,p['init/xsize'],160),np.linspace(0,p['init/ysize'],100));ids=np.full(x.shape,-1);T=np.full(x.shape,np.nan)
    def coords(row):
        return np.array([float(t[1:]) if t.startswith('m') else float(t)*(p['init/xsize'] if i%2==0 else p['init/ysize']) for i,t in enumerate(row)]).reshape(4,2)
    def region(c):
        # Source simple quadrilaterals have straight top/bottom edges between left/right x.
        left,right=c[0,0],c[2,0]
        if right<=left or c[1,0]!=left or c[3,0]!=right:raise ValueError('Preview needs quadrilaterals with vertical sides')
        f=(x-left)/(right-left);top=c[0,1]+f*(c[2,1]-c[0,1]);bottom=c[1,1]+f*(c[3,1]-c[1,1])
        return (x>=left)&(x<=right)&(y>=top)&(y<=bottom),f,(y-top)/np.maximum(bottom-top,1e-30),top
    for row in a['boxes']:
        if int(row[0]) not in {0,2}:raise ValueError('Direct preview only implements simple material boxes (types 0,2)')
        c=coords(row[2:]);mask,*_=region(c);ids[mask]=int(row[1].lstrip('i'))%100
    for row in a['temperatures']:
        kind=int(row[0]);mask,f,d,top=region(coords(row[1:9]));t=[float(v) for v in row[9:]]
        if kind==0:value=(t[0]+d*(t[1]-t[0]))*(1-f)+(t[2]+d*(t[3]-t[2]))*f
        elif kind==4:
            age=(t[4]+(t[5]-t[4])*f)*365.25*86400
            value=(t[1]+(t[3]-t[1])*f)-erfc((y-top)/(2*np.sqrt(np.maximum(t[6]*age,1))))*((t[1]-t[0])*(1-f)+(t[3]-t[2])*f)
        else:raise ValueError('Unsupported direct temperature structure '+str(kind))
        T[mask]=value[mask]
    mode=solver.parse_mode((Path(case['path'])/'mode.t3c').read_text())['parameters'];errors={}
    fields={'temperature':T};rho=np.full(x.shape,np.nan);eta=rho.copy()
    for rid,r in a['rocks'].items():
        mask=ids==rid
        if not mask.any():continue
        density_mode=mode.get('mode/densimod',1)
        rho[mask]=r['markro'] if density_mode==0 else r['markro']*(1-r['markbb']*(T[mask]-298.15))*(1-r['markaa']*1e-3)
        if density_mode>=2:errors['density']='Thermodynamic phase-table density is not implemented by the direct evaluator.'
        if r['markn0']==r['markn1']:eta[mask]=r['markn0']
        elif r['markdh']==0 and r['markdv']==0 and (r['markss']==0 or r['markmm']==1) and r['marknu']>0:eta[mask]=np.clip(r['marknu'],r['markn0'],r['markn1'])
        else:errors['viscosity']='This nonlinear I2VIS rheology is not implemented by the direct evaluator. Its marknu coefficient must not be displayed as viscosity.'
    fields.update(density=rho,viscosity=eta)
    coupling=Path(case['path'])/'assets/image-coupling.json'
    if coupling.exists():
        import json
        spec=json.loads(coupling.read_text());r=a['rocks'][spec['material_id']];mask=ids==spec['material_id'];target=ascii_field(coupling.parent,'image-density.dat',x,y)
        fields['density'][mask]=target[mask]
        fields['temperature'][mask]=298.15+(1-target[mask]/(r['markro']*(1+r['markaa']*(spec['pressure_bar']-1)*1e-3)))/r['markbb']
    for key in errors:fields.pop(key,None)
    return x,y,fields,errors,['I2VIS: Cartesian y is depth downward; source type-0/type-4 initial temperature. Density uses markro and markbb at P=0. Viscosity is drawn only for fixed bounds or simple Newtonian laws; nonlinear coefficients are not treated as viscosity. Thermodynamic phase diagrams and hydration are not evaluated.'],True

def render(case,target):
    import os,json
    os.environ.setdefault('MPLCONFIGDIR',str(storage.DATA/'plot-cache'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt,colors
    x,y,fields,errors,notes,invert=(i2vis if case['engine']=='i2vis' else aspect)(case)
    target.mkdir(parents=True,exist_ok=True);ranges={};files={}
    for key,v in fields.items():
        if not np.isfinite(v).all() or (np.any(v<0) if key=='temperature' else np.any(v<=0)):
            errors[key]='Undefined or nonpositive initial field; check domain coverage and material values';continue
        unit={'density':'kg/m³','viscosity':'Pa·s','temperature':'K'}[key];ranges[key]={'min':float(v.min()),'max':float(v.max()),'unit':unit}
        norm=colors.LogNorm(vmin=v.min(),vmax=v.max()) if key=='viscosity' and v.max()/v.min()>10 else None
        fig,ax=plt.subplots(figsize=(6,3.6));im=ax.pcolormesh(x,y,v,shading='auto',cmap='magma' if key=='temperature' else 'viridis',norm=norm)
        ax.set(xlabel='x (m)',ylabel='depth (m)' if invert else 'y (m)',aspect='equal')
        if invert:ax.invert_yaxis()
        fig.colorbar(im,ax=ax,label=unit);fig.tight_layout();fig.savefig(target/(key+'.png'),dpi=140);plt.close(fig);files[key]=str(target/(key+'.png'))
    localized=[]
    for note in notes:
        if note.startswith('Density:'):localized.append('密度：参考密度按体积分数混合，并计入线性热膨胀；不计压缩性。参考温度 '+note.rsplit('temperature ',1)[-1])
        elif note.startswith('Simple-model viscosity'):localized.append('简单材料黏度：根据输入的参考黏度和温度指数计算；不求解速度场。')
        elif note.startswith('Reference creep viscosity:'):localized.append('参考蠕变黏度：使用输入的参考应变率，压力为 0 Pa，调和混合；不计塑性屈服、弱化、相变、弹性及速度场耦合。它不是模拟求解得到的有效黏度。')
        elif note.startswith('I2VIS:'):localized.append('I2VIS：纵坐标向下为深度；读取类型 0/4 的初始温度。密度由参考密度与热膨胀系数在零压力下计算；黏度仅绘制固定上下限或简单牛顿流变；不把非线性流变系数当成黏度。不计算热力学相图和水化过程。')
        else:localized.append(note)
    metadata={'source':'Direct evaluation of input parameters; no simulator launched','ranges':ranges,'notes':notes,'notes_zh':localized,'field_errors':errors,'files':files}
    (target/'metadata.json').write_text(json.dumps(metadata,indent=2));return metadata
