"""Owned POSIX group cleanup; a denied signal is never evidence of termination."""
import os
import signal
import subprocess
import sys

MAX_PROCESS_TABLE=2*1024**2
CHECKS=('not_needed','kernel_absent','process_table_absent','process_table_zombies','unproven')


def group_state(group):
    # The observed empty-group EPERM occurs on the Mac host. Do not reinterpret
    # permission denials on Linux, where process-table visibility may be restricted.
    if sys.platform!='darwin':return 'unproven'
    try:
        result=subprocess.run(['/bin/ps','-A','-o','pgid=,state='],stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=2)
        if result.returncode or not result.stdout or len(result.stdout)>MAX_PROCESS_TABLE:return 'unproven'
        own=os.getpgrp();seen_own=False;states=[]
        for line in result.stdout.decode('ascii').splitlines():
            values=line.split()
            if len(values)!=2 or not values[0].isdigit() or not values[1] or len(values[1])>16:return 'unproven'
            identity=int(values[0]);state=values[1]
            if identity==own and not state.startswith('Z'):seen_own=True
            if identity==group:states.append(state)
        if not seen_own:return 'unproven'
        if not states:return 'absent'
        return 'zombies' if all(state.startswith('Z') for state in states) else 'unproven'
    except (OSError,UnicodeError,subprocess.TimeoutExpired):return 'unproven'


def signal_group(process,signum):
    if getattr(process,'_axiom_group_ended',False):return
    previous=getattr(process,'_axiom_group_signal_error',None)
    if previous is not None:raise previous
    try:os.killpg(process.pid,signum)
    except ProcessLookupError:
        process._axiom_group_ended=True;process._axiom_group_absence_check='kernel_absent'
    except PermissionError as exc:
        process._axiom_group_signal_denied=True;state=group_state(process.pid)
        if state in ('absent','zombies'):
            process._axiom_group_ended=True;process._axiom_group_absence_check='process_table_'+state
            return
        process._axiom_group_absence_check='unproven';process._axiom_group_signal_error=exc
        raise


def stop(process,*,graceful=False):
    signal_group(process,signal.SIGTERM if graceful else signal.SIGKILL)
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        signal_group(process,signal.SIGKILL);process.wait(timeout=2)
    if graceful:signal_group(process,signal.SIGKILL)


def observations(process):
    return {'cleanup_signal_permission_denied':bool(process is not None and getattr(process,'_axiom_group_signal_denied',False)),
        'cleanup_absence_check':'not_needed' if process is None else getattr(process,'_axiom_group_absence_check','not_needed')}


def consistent(observation):
    keys={'cleanup_signal_permission_denied','cleanup_absence_check'}&set(observation)
    if not keys:return True
    if len(keys)!=2:return False
    denied=observation['cleanup_signal_permission_denied'];check=observation['cleanup_absence_check']
    if type(denied)is not bool or check not in CHECKS or check=='unproven':return False
    if observation.get('process_started') is False and (denied or check!='not_needed'):return False
    return denied==(check in ('process_table_absent','process_table_zombies'))
