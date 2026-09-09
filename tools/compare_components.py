#!/usr/bin/env python3
"""Compare raw E5000 component files with separately read installed versions.

Offline normal-mode selection only. Does not authorize or perform an update.
"""
import argparse
import json
from pathlib import Path
from inspect_firmware import inspect


def version(value):
    parts = tuple(int(p) for p in value.split('.'))
    if len(parts) != 4 or any(p < 0 or p > limit for p, limit in zip(parts, (15, 15, 255, 255))):
        raise ValueError('Expected four version fields: major.minor.patch.build')
    return parts


def compare(target, installed):
    """Th.v3 normal mode / Mh.l: differences select either upgrade or downgrade."""
    target = version(target)
    if installed is None:
        return 'read-required'
    installed = version(installed)
    if installed[1] == 15 and target[1] != 15:
        return 'recovery-state-unresolved'
    return 'upgrade' if target > installed else 'downgrade' if target < installed else 'equal'


def plan(d_data, m_data, installed_d=None, installed_m=None):
    d, m = inspect(d_data), inspect(m_data)
    if d['component'] != 'D' or m['component'] != 'M':
        raise ValueError('Provide D and M images in that order')
    components = {}
    for name, header, installed in [('M', m, installed_m), ('D', d, installed_d)]:
        components[name] = dict(target=header, installed=installed,
                                comparison=compare(header['version'], installed))
    unresolved = any(c['comparison'] in ('read-required', 'recovery-state-unresolved')
                     for c in components.values())
    return dict(components=components,
                normal_mode_order=None if unresolved else [name for name, c in components.items()
                    if c['comparison'] != 'equal'],
                installable=False,
                limitations=['normal mode only; forced rewriting and recovery are not modeled',
                             'installed values require independent D and M native reads',
                             'target provenance, compatibility and transfer recovery unverified'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('d_file', type=Path)
    parser.add_argument('m_file', type=Path)
    parser.add_argument('--installed-d')
    parser.add_argument('--installed-m')
    args = parser.parse_args()
    try:
        images = []
        for path in (args.d_file, args.m_file):
            with path.open('rb') as f:
                images.append(f.read(32 * 1024 * 1024 + 1))
        result = plan(*images, args.installed_d, args.installed_m)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
