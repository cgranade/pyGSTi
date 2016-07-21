#!/usr/bin/env python3
from __future__                import print_function
from helpers.test.helpers      import *
from helpers.test._getCoverage import _read_coverage
from helpers.automation_tools  import read_yaml, write_yaml, directory
import importlib
import inspect
import time
import sys
import os


def get_test_files(dirname, extension='.py'):
    testFiles = []
    for subdir, dirs, files in os.walk(dirname):
        for filename in files:
            filepath = subdir + os.sep + filename
            if filename.endswith(extension) and filename.startswith('test'):
                testFiles.append((filepath, filename))
    return testFiles

def find_individual_tests(testCase):
    istest = lambda a, case : callable(getattr(case, a)) and a.startswith('test')
    return [attr for attr in dir(testCase) if istest(attr, testCase)]

def parse_coverage_output(filename):
    with open(filename) as content:
        specific = content.read().split('-----------------------------------------------')[1]
        specific = [line for line in specific.replace('-', '').splitlines() if line != '']
    
    # At this point, specific looks like this:
    '''
    pygsti/objects.py                       21      0   100%
    pygsti/objects/confidenceregion.py     213    195     8%
    pygsti/objects/dataset.py              262    200    24%
    pygsti/objects/evaltree.py             255    235     8%
    pygsti/objects/exceptions.py             5      0   100%
    pygsti/objects/gate.py                 331    215    35%
    pygsti/objects/gateset.py              489    346    29%
    pygsti/objects/gatestring.py           151    115    24%
    pygsti/objects/gscalc.py              1189   1095     8%
    pygsti/objects/labeldicts.py           113     41    64%
    pygsti/objects/multidataset.py         159    122    23%
    pygsti/objects/protectedarray.py       121     73    40%
    pygsti/objects/spamspec.py              14      8    43%
    pygsti/objects/spamvec.py              158     71    55%
    pygsti/objects/verbosityprinter.py     113     81    28%
    '''
    coverageDict = {}
    for line in specific:
        filename, _, _, percentage = line.split()
        coverageDict[filename] = int(percentage[:-1]) # Cut off percent symbol
    return coverageDict


def get_test_info(filename, packageName, testCaseName, test):
    coverageFile = '../../output/individual_coverage/%s.out' % (test)
    commands = ['nosetests', '-v', '--with-coverage', '--cover-package=pygsti.%s' % packageName, 
                '--cover-erase', '%s:%s.%s' % (filename, testCaseName, test), 
                '2>&1 | tee %s' % coverageFile]
    start   = time.time()
    percent = _read_coverage(' '.join(commands), coverageFile)
    end     = time.time()

    coverageDict = parse_coverage_output(coverageFile)
    write_yaml(coverageDict, coverageFile)
    
    return ((end - start), percent)

def gen_individual_test_info(packageName):
    testsInfo = {}

    dirname = os.getcwd() + '/test_packages/' + packageName + '/'
    for _, filename in get_test_files(dirname):
        moduleName = 'test_packages.' + packageName + '.' + filename[:-3]
        print('Finding slow tests in %s' % moduleName)
        i = importlib.import_module(moduleName)
        testCases = inspect.getmembers(i, predicate=inspect.isclass)
        for testCaseName, testCase in testCases:
            tests = find_individual_tests(testCase)
            for testName in tests:
                testcase = testCase()
                testcase.setUp()
                info = get_test_info(filename, packageName, testCaseName, testName)
                testsInfo[filename[:-3] + '.' + testCaseName + '.' + testName] = info
                testcase.tearDown()

    return testsInfo
                
if __name__ == '__main__':

    gen_info_on = sys.argv[1:]
    infoDict    = read_yaml('output/all_individual_test_info.yml')
    if infoDict is None: # if the file is empty
        infoDict = {}

    # Update info for the packages given 
    for packageName in gen_info_on:
        print('Updating info for %s' % packageName)
        infoDict[packageName] = gen_individual_test_info(packageName)

    write_yaml(infoDict, 'output/all_individual_test_info.yml')