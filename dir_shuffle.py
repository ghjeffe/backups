import pathlib, shutil, os

os.chdir('testing')

test_dirs = list(pathlib.Path('.').glob('testdir*'))
for testdir in sorted(test_dirs, key=lambda x: x.name.split('.')[1], reverse=False):
    base, extn = testdir.name.split('.')
    new_dir = '{}.{}'.format(base, str(int(extn) - 1).zfill(2))
    shutil.move(testdir.name, new_dir)
    print('{} becomes {}'.format(testdir.name, new_dir))
