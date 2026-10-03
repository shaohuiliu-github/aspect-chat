"""Produce public source and offline bundles; never ship a used workspace."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile

parser=argparse.ArgumentParser();parser.add_argument('context',type=Path);parser.add_argument('output',type=Path)
parser.add_argument('--arch',choices=['arm64','amd64','universal','source','online'],required=True);parser.add_argument('--image',type=Path)
parser.add_argument('--amd64-image',type=Path)
parser.add_argument('--registry',default='ghcr.io/shaohuiliu-github/aspect-chat:2.0.4')
parser.add_argument('--registry-verified',action='store_true',help='Record a completed anonymous registry verification')
args=parser.parse_args();context=args.context.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
name='chatGFD-2.0.4-'+args.arch;root=out/name;root.mkdir(exist_ok=True)
for name_in in ('start.sh','start.ps1','Start.bat','Stop.bat','host_bridge.py','使用说明.md','README-English.md','LICENSE-NOTICES.md'):
    shutil.copy2(context/'packaging'/name_in,root/name_in)
if (context/'app/DEMO_CASES.md').exists(): shutil.copy2(context/'app/DEMO_CASES.md',root/'DEMO_CASES.md')
if args.arch!='online':
    for name_in in ('app','knowledge','packaging'):
        shutil.copytree(context/name_in,root/'source'/name_in,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(context/'packaging/LICENSE-AGPL-3.0.txt',root/'source/LICENSE-AGPL-3.0.txt')
else:
    (root/'image-reference.txt').write_text(args.registry+'\n')
    shutil.copy2(context/'packaging/LICENSE-AGPL-3.0.txt',root/'LICENSE-AGPL-3.0.txt')
archives=[(args.arch,args.image)] if args.image else []
if args.arch=='universal':
    if not args.image or not args.amd64_image: parser.error('Universal release requires both architecture images')
    archives=[('arm64',args.image),('amd64',args.amd64_image)]
checksums=[]
for architecture,input_image in archives:
    images=root/'images';images.mkdir(exist_ok=True);image=images/f'aspect-chat-{architecture}.tar.gz'
    if image.exists() and not image.samefile(input_image.resolve()): image.unlink()
    if not image.exists():
        try: image.hardlink_to(input_image.resolve())
        except OSError: shutil.copy2(input_image,image)
    digest=hashlib.sha256()
    with image.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): digest.update(block)
    checksums.append(digest.hexdigest()+'  images/'+image.name)
if checksums: (root/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
(root/'workspace/inputs').mkdir(parents=True,exist_ok=True)
(root/'workspace/README.txt').write_text('Your models, outputs and API key will be stored here. Do not redistribute a used workspace.\n')
manifest=json.loads((context/'knowledge/manifest.json').read_text())
manifest.update({'package':'chatGFD 2.0.4','architecture':args.arch,'offline_image_included':bool(args.image),'workspace_included':'empty scaffold only','registry_target':args.registry,'registry_publication_verified':args.registry_verified})
(root/'发布信息.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
report=out/'容器验证报告.json'
if report.exists(): shutil.copy2(report,root/'验证报告.json')
archive=out/(root.name+'.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
    for file in sorted(root.rglob('*')):
        if not file.is_file() or file.is_symlink(): continue
        relative=file.relative_to(root)
        # A launcher may have been run in the distribution directory during QA.
        if relative.parts[0]=='workspace' and relative.as_posix()!='workspace/README.txt': continue
        if '__pycache__' in relative.parts or file.suffix=='.pyc': continue
        compression=zipfile.ZIP_STORED if file.suffix=='.gz' else zipfile.ZIP_DEFLATED
        z.write(file,arcname=root.name+'/'+relative.as_posix(),compress_type=compression)
print(json.dumps({'folder':str(root),'zip':str(archive),'bytes':archive.stat().st_size}))
