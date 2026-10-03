"""Three-dimensional inputs are shown as explicit central sections, never flattened."""
import numpy as np
from aspect_chat import cases,initial_fields,prm,storage
from test_chatgfd import isolated,MODEL


def test_central_slice_uses_physical_xyz_and_custom_names(tmp_path):
    text=prm.patch(MODEL,{'Dimension':'3','Geometry model/Box/Z extent':'200','Geometry model/Box/Box origin Y coordinate':'50','Geometry model/Box/Box origin Z coordinate':'10','Initial temperature model/Function/Variable names':'a,b,c,time','Initial temperature model/Function/Function expression':'300+a/100+b/10+c+time'},allow_new=True)
    c=cases.create('3D',text)['case_id'];case=storage.get_case(c)
    x,z,fields,errors,notes,invert=initial_fields.aspect(case)
    assert not errors and not invert
    # y is the centre of [50,550], z spans [10,210], t=0; y must not mean z.
    assert np.allclose(fields['temperature'],300+x/100+30+z)
    meta=initial_fields.render(case,tmp_path/'maps')
    assert meta['slice']=={'axes':['x','z'],'fixed_axis':'y','coordinate_m':300}
    assert len(meta['files'])==3 and meta['scales']['viscosity']=='log'
    assert storage.query('SELECT * FROM jobs')==[]


def test_3d_ascii_input_is_not_silently_interpreted_as_2d():
    text=prm.patch(MODEL,{'Dimension':'3','Geometry model/Box/Z extent':'500','Initial temperature model/Model name':'ascii data'},allow_new=True)
    c=cases.create('3D-ascii',text)['case_id']
    _,_,_,errors,_,_=initial_fields.aspect(storage.get_case(c))
    assert '3D ASCII' in errors['temperature']
