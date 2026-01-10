#!/usr/bin/env python3
import os
import glob
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / 'packages'
PACKAGES_DIR.mkdir(exist_ok=True)


def load_manifest(manifest_path: Path):
    text = manifest_path.read_text(encoding='utf-8')
    idx = text.find('{')
    if idx == -1:
        raise ValueError(f"No dict literal found in {manifest_path}")
    wrapper = text[:idx] + 'MANIFEST = ' + text[idx:]
    env = {}
    try:
        exec(wrapper, {}, env)
    except Exception as e:
        raise RuntimeError(f"Failed to exec {manifest_path}: {e}")
    if 'MANIFEST' not in env:
        raise RuntimeError(f"MANIFEST not found after exec of {manifest_path}")
    return env['MANIFEST']


REQUIRED_KEYS = ['name', 'version', 'license']


def validate_module(module_path: Path):
    report = {'module': str(module_path.relative_to(ROOT)), 'manifest_ok': True, 'missing_keys': [], 'xml_errors': []}
    manifest_file = module_path / '__manifest__.py'
    if not manifest_file.exists():
        report['manifest_ok'] = False
        report['error'] = '__manifest__.py missing'
        return report
    try:
        manifest = load_manifest(manifest_file)
    except Exception as e:
        report['manifest_ok'] = False
        report['error'] = f'manifest load error: {e}'
        return report
    for k in REQUIRED_KEYS:
        if k not in manifest:
            report['missing_keys'].append(k)
            report['manifest_ok'] = False
    # Validate referenced XML files and all xml files under module
    xml_files = set()
    data_list = manifest.get('data', []) or []
    for entry in data_list:
        entry_path = (module_path / entry)
        # Only validate XML files listed in manifest (skip CSVs and others)
        if entry_path.suffix.lower() == '.xml':
            xml_files.add(entry_path.resolve())
    # also include any xml under module
    for p in module_path.rglob('*.xml'):
        xml_files.add(p.resolve())
    for xf in sorted(xml_files):
        if not xf.exists():
            report['xml_errors'].append(f'Missing file: {xf.relative_to(ROOT)}')
            continue
        try:
            ET.parse(str(xf))
        except Exception as e:
            report['xml_errors'].append(f'{xf.relative_to(ROOT)} -> {e}')
    return report


def find_module_dirs(root: Path):
    mods = []
    for p in root.rglob('__manifest__.py'):
        mods.append(p.parent)
    return sorted(set(mods))


def package_module(module_path: Path, manifest):
    name = manifest.get('name') or module_path.name
    version = manifest.get('version') or '0.0.0'
    safe_name = module_path.name
    archive_name = f"{safe_name}-{version}"
    target = PACKAGES_DIR / archive_name
    # make_archive will append .zip
    shutil.make_archive(str(target), 'zip', root_dir=str(module_path))
    return PACKAGES_DIR / (archive_name + '.zip')


if __name__ == '__main__':
    print('Workspace root:', ROOT)
    module_dirs = find_module_dirs(ROOT)
    print(f'Found {len(module_dirs)} modules with __manifest__.py')
    reports = []
    ringcentral_root = None
    # Try to detect ringcentral suite folder explicitly for targeted packaging
    for md in module_dirs:
        if md.name == 'ringcentral_suite' and 'ringcentral_suite' in str(md):
            ringcentral_root = md.parent
            break
    for md in module_dirs:
        rep = validate_module(md)
        reports.append(rep)
        status = 'OK' if rep.get('manifest_ok') and not rep.get('xml_errors') else 'ISSUES'
        print(f"{md.relative_to(ROOT)}: {status}")
        if rep.get('missing_keys'):
            print('  Missing manifest keys:', rep['missing_keys'])
        if rep.get('xml_errors'):
            print('  XML issues:')
            for e in rep['xml_errors']:
                print('   -', e)
    # Package ringcentral submodules (modules under ringcentral_suite/ringcentral_suite-*/ )
    packaged = []
    if ringcentral_root:
        print('\nPackaging ringcentral submodules under', ringcentral_root)
        # find subdirs of ringcentral_root that contain __manifest__.py
        for sub in ringcentral_root.rglob('__manifest__.py'):
            md = sub.parent
            # skip the top-level suite folder packaged earlier
            if md.name == 'ringcentral_suite' and 'ringcentral_suite' in str(md):
                continue
            try:
                manifest = load_manifest(md / '__manifest__.py')
            except Exception as e:
                print('Skipping package for', md, 'due to manifest load error:', e)
                continue
            zipf = package_module(md, manifest)
            packaged.append(str(zipf.relative_to(ROOT)))
            print('  Packaged', md.relative_to(ROOT), '->', zipf.relative_to(ROOT))
    else:
        # Fallback: package any module under a directory named ringcentral_suite anywhere
        for md in module_dirs:
            if 'ringcentral' in md.name.lower() and md != ROOT:
                try:
                    manifest = load_manifest(md / '__manifest__.py')
                except Exception as e:
                    continue
                zipf = package_module(md, manifest)
                packaged.append(str(zipf.relative_to(ROOT)))
                print('  Packaged', md.relative_to(ROOT), '->', zipf.relative_to(ROOT))

    print('\nSummary:')
    print('Validation reports:', len(reports))
    bad = [r for r in reports if not r.get('manifest_ok') or r.get('xml_errors')]
    print('Modules with issues:', len(bad))
    if packaged:
        print('Created packages:')
        for p in packaged:
            print(' -', p)
    else:
        print('No individual ringcentral submodule packages created.')

    # write a simple report file
    rpt = ROOT / 'validate_report.txt'
    with rpt.open('w', encoding='utf-8') as f:
        for r in reports:
            f.write(str(r) + '\n')
        if packaged:
            f.write('\nPackages:\n')
            for p in packaged:
                f.write(p + '\n')
    print('\nReport written to', rpt.relative_to(ROOT))
