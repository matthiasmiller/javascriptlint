import os.path
import subprocess

try:
    from __svnversion__ import version
except ImportError:
    def _getrevnum():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = subprocess.Popen(['svnversion', path], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise _BuildError('Error running svnversion: %s' % stderr)
        version = stdout.strip().rstrip('M')
        version = version.rpartition(':')[-1]
        return int(version)

    version = '0.5.0/r%i' % _getrevnum()

