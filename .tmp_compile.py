import py_compile, glob, sys
files = glob.glob('app/*.py') + glob.glob('app/*/*.py') + glob.glob('app/*/*/*.py')
errors = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        print('ERROR', f, e)
        errors += 1
print('DONE', len(files), 'files checked, errors=', errors)
sys.exit(errors)
