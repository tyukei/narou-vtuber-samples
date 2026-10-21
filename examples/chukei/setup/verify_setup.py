"""Check command-line failure paths; optionally run real Linux integration checks.

The integration run installs/starts the documented packages, plays a synthetic
tone into a null sink, records only that sink's monitor, and stops its resources.
"""
import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import urllib.request
import wave

HERE = Path(__file__).resolve().parent
SCRIPT = HERE/'vtuber.sh'


def run(*args, check=True):
    result = subprocess.run(args, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f'{args}:\n{result.stdout}\n{result.stderr}')
    return result


def call(command, directory, *options, check=True):
    return run('bash', str(SCRIPT), command, '--dir', str(directory), *options, check=check)


def cli_checks():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'not created yet'
        assert call('setup', path, '--dry-run').returncode == 0
        assert not path.exists(), 'dry-run wrote to disk'
        for options in (('--port','0'), ('--port','65536'), ('--port','abc'),
                        ('--timeout','0'), ('--dir','/'), ('--dir',''), ('--dir','a:b'),
                        ('--port',), ('--unknown',)):
            result = call('start', path, *options, check=False)
            assert result.returncode != 0, options
            assert not path.exists(), 'invalid argument created a directory'
        assert run('bash', str(SCRIPT), '--help').returncode == 0
        assert call('nonsense', path, check=False).returncode != 0
    return ['dry-run creates no files', 'invalid arguments fail before mutation', 'help']


def integration(directory):
    directory = directory.resolve()
    checks = []
    port = '18889'
    suffix = call('start', directory, '--dry-run', '--port', port).stdout
    sink = next(line.split('音声: ')[1].split('（')[0] for line in suffix.splitlines() if line.startswith('音声: '))
    started = False
    try:
        call('setup', directory)
        before = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (directory/'obs-config').rglob('*') if p.is_file()}
        call('setup', directory)
        assert all(hashlib.sha256((directory/p).read_bytes()).hexdigest() == h for p,h in before.items())
        checks.append('setup preserves existing profile and scene files')
        started = True  # stop also cleans resources left by a failed start.
        call('start', directory, '--no-open', '--port', port)
        html = urllib.request.urlopen(f'http://localhost:{port}/',timeout=5).read()
        assert b'<html' in html.lower()
        info = json.load(urllib.request.urlopen(f'http://localhost:{port}/info',timeout=5))
        assert 'modelSlots' in info
        checks.append('VC Client HTML and /info return valid responses')
        # Allow the GUI to finish loading the supplied collection.
        for _ in range(20):
            log = (directory/'obs.log').read_text(errors='replace')
            if "Switched to scene 'Avatar'" in log: break
            time.sleep(1)
        assert "Switched to scene 'Avatar'" in log, log[-1000:]
        assert '--profile Isekai --collection Isekai' in log
        checks.append('OBS launches the Isekai profile and Avatar scene')
        pid = (directory/'obs.pid').read_text()
        module = (directory/'audio.module').read_text()
        call('start', directory, '--no-open', '--port', port)
        assert (directory/'obs.pid').read_text() == pid
        assert (directory/'audio.module').read_text() == module
        checks.append('repeat start reuses OBS and the virtual audio module')
        with tempfile.TemporaryDirectory() as temp:
            tone, recorded = Path(temp)/'tone.wav', Path(temp)/'recorded.wav'
            samples = array.array('h', (int(12000*math.sin(2*math.pi*1000*n/48000)) for n in range(24000)))
            with wave.open(str(tone),'wb') as wav:
                wav.setparams((1,2,48000,0,'NONE','not compressed'))
                wav.writeframes(samples.tobytes())
            recorder = subprocess.Popen(['parecord','--device',sink+'.monitor','--rate=48000',
                                         '--channels=1','--latency-msec=50','--format=s16le','--file-format=wav',str(recorded)],
                                        stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                time.sleep(1.0)
                run('paplay','--device',sink,str(tone))
                time.sleep(1.0)
            finally:
                recorder.send_signal(signal.SIGINT)
                recorder.wait(timeout=5)
            with wave.open(str(recorded),'rb') as wav:
                data = array.array('h', wav.readframes(wav.getnframes()))
            assert data, 'Monitor recording is empty: '+recorder.stderr.read().decode(errors='replace')
            rms = math.sqrt(sum(x*x for x in data)/len(data))
            assert rms > 1000 and max(data) > 5000, f'RMS={rms}'
            checks.append(f'1000Hz tone reaches the virtual microphone (RMS={rms:.1f})')
        call('stop', directory)
        time.sleep(2)
        status = call('status', directory).stdout
        assert 'VC Client: 停止' in status and '仮想音声: 未作成' in status and 'OBS: 停止' in status
        checks.append('stop removes the container and audio sink, and closes OBS')
        call('stop', directory)
        call('start', directory, '--no-open', '--port', port)
        assert '起動中' in call('status', directory).stdout
        checks.append('stop is repeatable and a subsequent start succeeds')
        call('stop', directory)
        # Simulate a saved module number being reused by another null sink.
        fixture = 'vtuber_verification_'+str(os.getpid())
        other = run('pactl','load-module','module-null-sink','sink_name='+fixture).stdout.strip()
        try:
            (directory/'audio.module').write_text(other+'\n')
            call('stop',directory)
            assert fixture in run('pactl','list','short','sinks').stdout
            checks.append('stale module ids do not remove a different audio device')
        finally:
            run('pactl','unload-module',other)
        return checks
    finally:
        if started:
            call('stop', directory, check=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--integration',action='store_true')
    parser.add_argument('--dir',type=Path,default=Path.home()/'.local/share/isekai-vtuber-verification')
    args = parser.parse_args()
    results = cli_checks()
    if args.integration:
        results += integration(args.dir)
    print(json.dumps({'passed':results},ensure_ascii=False,indent=2))
