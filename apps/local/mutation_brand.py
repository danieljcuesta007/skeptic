"""Exercise local palette/contrast faults in memory, without editing CSS."""
from pathlib import Path
import unittest
from unittest.mock import patch
import app
import test_app


def main():
    target = app.HERE / 'style.css'
    original = Path.read_text
    css = original(target)
    faults = [
        ('colored wordmark', '.brand span{color:var(--ink)}', '.brand span{color:#FF2800}', 'test_monochrome_palette'),
        ('invisible selected navigation', 'background:#fff;color:#000;font-weight:700', 'background:#fff;color:#fff;font-weight:700', 'test_monochrome_control_contrast'),
    ]
    for name, old, new, method in faults:
        if css.count(old) != 1: raise AssertionError('Mutation anchor: ' + name)
        def read(path, *args, **kwargs):
            return css.replace(old, new) if path == target else original(path, *args, **kwargs)
        result = unittest.TestResult()
        with patch.object(Path, 'read_text', read):
            unittest.defaultTestLoader.loadTestsFromName('ServerTests.' + method, test_app).run(result)
        if not result.failures or result.errors: raise AssertionError('Expected regression did not catch: ' + name)
        print('Caught local brand fault:', name)
    print(f'{len(faults)} local brand mutations caught.')


if __name__ == '__main__': main()
