import pathlib, shutil, os

os.chdir('testing')
keep_count = 21

test_dirs = list(pathlib.Path('.').glob('testdir*'))
for testdir in sorted(test_dirs, key=lambda x: int(x.name.split('.')[1]), reverse=True):
    base, extn = testdir.name.split('.')
    if int(extn) == keep_count:
        shutil.rmtree(testdir.name)
    else:
        dir_becomes = '{}.{}'.format(base, str(int(extn) + 1).zfill(2))
        testdir.rename(dir_becomes)
        print('{} becomes {}'.format(testdir.name, dir_becomes))
os.mkdir('testdir.00')
