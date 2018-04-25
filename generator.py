import os, sys, glob, shutil, ctypes
args = sys.argv
import nuke

FOLDERS = ['dailies', 'hires', 'nuke', 'prm', 'scan']


def create_shot_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            print('Error create path {}'.format(path))
            return False
    for sub in FOLDERS:
        sub_dir = os.path.join(path, sub)
        if not os.path.exists(sub_dir):
            try:
                os.makedirs(sub_dir)
            except:
                print('Error create path {}'.format(path))
                return False
    return True


def is_admin():
    if os.name == 'nt':
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    else:
        return os.geteuid() == 0


__CSL = None


def _windows_symlink(source, link_name):
    # http://blog.bfitz.us/?p=2035
    global __CSL
    if __CSL is None:
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        __CSL = csl
    flags = 0
    if source is not None and os.path.isdir(source):
        flags = 1
    if __CSL(link_name, source, flags) == 0:
        raise ctypes.WinError()


def link(source_path, target_path):
    if os.path.exists(target_path):
        print('Path already exists: {}'.format(target_path))
        return False
    if os.name == 'nt':
        if not is_admin():
            print('Require admin privileges')
        _windows_symlink(os.path.normpath(source_path), os.path.normpath(target_path))
        # cmd = 'mklink{isdir} {trg} {src}'.format(
        #     isdir=' /D' if os.path.isdir(source_path) else '',
        #     src=os.path.normpath(source_path),
        #     trg=os.path.normpath(target_path)
        # )
        # os.system(cmd)
    else:
        cmd = 'ln -s {}  {}'.format(source_path, target_path)
        os.system(cmd)
    return os.path.exists(target_path)


def verb(*args):
    print ' '.join(*args)


def generate(refscript, movdir, dpxdir, outdir):
    devnull = open(os.devnull, 'wb')
    mov_files = glob.glob1(movdir, '*.mov')
    for mov in mov_files:
        mov_path = os.path.normpath(os.path.join(movdir, mov))
        # load script
        # break
        nuke.scriptOpen(refscript)
        shot_name = mov.split('_', 1)[0]
        print(shot_name)
        # shot_name = 'che0010'
        out_shot_dir = os.path.normpath(os.path.join(outdir, shot_name))
        create_shot_dir(out_shot_dir)
    
        # prm
        shutil.copy2(mov_path, os.path.join(out_shot_dir, 'prm', mov))
    
        # dpx
        last_frame_dpx = 1
        shot_dpx_dir = os.path.normpath(os.path.join(dpxdir, shot_name))
        if os.path.exists(shot_dpx_dir):
            if not os.path.exists(shot_dpx_dir):
                print('DPX for shot {} not found'.format(shot_name))
            dpx_files = os.listdir(shot_dpx_dir)
            for i, d in enumerate(dpx_files, 1):
                old = os.path.join(shot_dpx_dir, d)
                new = os.path.join(out_shot_dir, 'scan', '{}_v000.{:04d}.dpx'.format(shot_name, i))
                if os.path.exists(new):
                    os.remove(new)
                link(old, new)
                last_frame_dpx = i
        else:
            print('DPX sources not found for {}'.format(shot_name))
        # edit script
        # read DPX
        ReadPRM = nuke.toNode('ReadPRM')
        if not ReadPRM:
            print('node ReadPRM not found')
        else:
            read_path = '[python os.path.dirname(nuke.script_directory())]/scan/{}_v000.####.dpx'.format(shot_name)
            ReadPRM['file'].setValue(read_path)

        ReadMOV = nuke.toNode('ReadMOV')
        if not ReadMOV:
            print('node ReadMOV not found')
        else:
            read_path = '[python os.path.dirname(nuke.script_directory())]/prm/{}'.format(mov)
            ReadMOV['file'].fromUserText(read_path)

        # write
        WriteHR = nuke.toNode('WriteHR')
        if not WriteHR:
            print('node WriteHR not found')
        else:
            out_hires = '[python os.path.dirname(nuke.script_directory())]/hires/{}_v000.####.dpx'.format(shot_name)
            WriteHR['file'].setValue(out_hires)

        # dailise
        WriteDailise = nuke.toNode('WriteDailise')
        if not WriteDailise:
            print('node WriteDailise not found')
        else:
            out_hires = '[python os.path.dirname(nuke.script_directory())]/dailies/{}_comp_v001.mov'.format(shot_name)
            WriteDailise['file'].setValue(out_hires)

        # backdrop
        ShotName = nuke.toNode('ShotName')
        if not ShotName:
            print('node ShotName not found')
        else:
            ShotName['label'].setValue('<center>' + shot_name)

        # root
        nuke.root()['first_frame'].setValue(100)
        nuke.root()['last_frame'].setValue(last_frame_dpx+100)
        nuke.root()['lock_connections'].setValue(True)
        out_script = os.path.join(out_shot_dir, 'nuke', '{}_comp_v000.nk'.format(shot_name))
        out_script = os.path.normpath(out_script).replace('\\', '/')
        _ = sys.stdout
        sys.stdout = devnull
        nuke.scriptSaveAs(out_script, True)
        sys.stdout = _
        
if __name__ == '__main__':
    if len(args[1:]) < 4:
        print(args[1:])
        print('Error arguments')
        sys.exit()
    refscript, movdir, dpxdir, outdir = args[1:]

    generate(refscript, movdir, dpxdir, outdir)
