from pathlib import Path
import re,sys
root=Path(sys.argv[1]);base=(root/'mode.t3c').read_text();cut=base.index('~')
mode='/LOADFILE\ninitial h\n/SAVEFILE_TYPE_CYCLES_DISPLACEMENT_TEMPERATURE_TIMESTEP_YEARS\nresult001 h 2 0.05 100 1000\n'+base[cut:]
for key,value in {'erosmod':'0','meltmod':'0','densimod':'1','timebond':'2000','frictyn':'0','adiabyn':'0','FSSA':'0','markmod':'1','filestop':'20','waterlev':'0','eroslev':'0','sedilev':'0'}.items():mode=re.sub(r'[^\s/]+-'+key+r'(?=\s|$)',value+'-'+key,mode)
bc='''/BOUNDARY_CONDITIONS
P 2 2 1 1 0 0 0 0
P 1 1 1 1 0 1 +1 +0 0 0
P 1 1 y y 0 1 +1 +0 0 0
P x x 1 1 0 1 -1 +0 0 0
P x x y y 0 1 -1 +0 0 0
Vx 0 x 0 0 0 1 0 +1 0 0
Vy 0 x-1 0 0 0 0 0 0
Vx 0 x y-1 y-1 0 1 0 -1 0 0
Vy 0 x-1 y y 0 0 0 0
Vx 0 0 1 y-2 0 0 0 0
Vy 0 0 1 y-1 0 1 +1 0 0 0
Vx x x 1 y-2 0 0 0 0
Vy x-1 x-1 1 y-1 0 1 -1 0 0 0
T 0 0 1 y-1 0 1 +1 0 0 0
T 0 x 0 0 300 0 0 0
T 0 x y y 1600 0 0 0
T x x 1 y-1 0 1 -1 0 0 0
~
'''
# Values correspond to in2fasth5.c's 24 material fields, never an ASPECT conversion.
def rock(i,rho,eta):return f'{i} {eta} {eta} 0 5e29 {eta} 0 0 0 1 0 0 0 0 0 0 1 {rho} 3e-5 0 1250 3 0 0 0\n'
header='/INPUT_GRID\n1-cartpolar\n41-xnumx\n21-ynumy\n4-mnumx\n4-mnumy\n1000000-xsize(m)\n500000-ysize(m)\n0-radius\n0-pinit\n0-GXKOEF\n9.81-GYKOEF\n0-timesum\n0-nonstab\n/MARKERS_FILE\n0\n/OUTPUT\ninitial.h5 h\n/ROCKS\n'
for name in ('rayleigh_taylor','mantle_plume'):
 init=header+rock(0,1,'1e17')+rock(2,3300,'1e21')+rock(3,3400,'1e20')+'~\n'+bc+'/MATERIAL_BOXES\n0 2 0 0 0 1 1 0 1 1\n'
 if name=='rayleigh_taylor':init+='0 3 0 0 0 .5 1 0 1 .55\n'
 init+='~\n/TEMPERATURE\n0 0 0 0 1 1 0 1 1 300 1600 300 1600\n'
 if name=='mantle_plume':init+='0 .4 .8 .4 1 .6 .8 .6 1 1700 1800 1700 1800\n'
 init+='~\n';d=root/'templates'/name;d.mkdir(parents=True,exist_ok=True);(d/'init.t3c').write_text(init);(d/'mode.t3c').write_text(mode)
init=(root/'init.t3c').read_text();init=init.replace('801-xnumx','81-xnumx').replace('201-ynumy','41-ynumy').replace('4-mnumx','4-mnumx').replace('4-mnumy','4-mnumy').replace('dsd000.h5','initial.h5')
d=root/'templates/subduction';d.mkdir(parents=True,exist_ok=True);(d/'init.t3c').write_text(init);(d/'mode.t3c').write_text(mode)
