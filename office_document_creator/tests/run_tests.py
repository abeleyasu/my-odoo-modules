#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Office Document Creator - Test Runner

Run comprehensive tests for the Office module.
Usage: python run_tests.py [options]

Options:
    --unit          Run unit tests only
    --integration   Run integration tests only
    --performance   Run performance tests only
    --all           Run all tests (default)
    --verbose       Show detailed output
    --fail-fast     Stop on first failure
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime

# Odoo path
ODOO_PATH = '/opt/odoo/odoo-18'
ODOO_BIN = os.path.join(ODOO_PATH, 'odoo-bin')
TEST_DB = 'test_office'

# Test tag groups
TEST_GROUPS = {
    'unit': ['office_document', 'office_folder', 'office_access', 'office_version', 'office_share'],
    'integration': ['office_integration'],
    'performance': ['office_performance'],
    'controller': ['office_controller'],
    'all': ['office'],
}


def run_tests(tags, verbose=False, fail_fast=False, db_name=TEST_DB):
    """Run tests with specified tags."""
    
    # Build command
    cmd = [
        'python3', ODOO_BIN,
        '-d', db_name,
        '-u', 'office_document_creator',
        '--test-tags', ','.join(tags),
        '--stop-after-init',
    ]
    
    if fail_fast:
        cmd.append('--test-failure-exit')
    
    print(f"\n{'='*60}")
    print(f"Running Office Module Tests")
    print(f"{'='*60}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tags: {', '.join(tags)}")
    print(f"Database: {db_name}")
    print(f"{'='*60}\n")
    
    # Run tests
    try:
        result = subprocess.run(
            cmd,
            cwd='/opt/odoo',
            capture_output=not verbose,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            if not verbose and result.stderr:
                print("\nError output:")
                print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        
        return result.returncode
        
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


def generate_test_report(tags, db_name=TEST_DB):
    """Generate test report."""
    print("\n" + "="*60)
    print("TEST REPORT SUMMARY")
    print("="*60)
    
    # Count test classes and methods
    test_files = [
        'test_office_document.py',
        'test_office_folder.py',
        'test_office_access.py',
        'test_office_version.py',
        'test_office_share.py',
        'test_office_controller.py',
        'test_office_integration.py',
        'test_office_performance.py',
    ]
    
    total_classes = 0
    total_methods = 0
    
    for test_file in test_files:
        file_path = os.path.join(
            '/opt/odoo/custom_addons/office_document_creator/tests',
            test_file
        )
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                classes = content.count('class Test')
                methods = content.count('def test_')
                total_classes += classes
                total_methods += methods
                print(f"  {test_file}: {classes} classes, {methods} tests")
    
    print("-"*60)
    print(f"  TOTAL: {total_classes} test classes, {total_methods} test methods")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Run Office Document Creator tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--controller', action='store_true', help='Run controller tests only')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fail-fast', action='store_true', help='Stop on first failure')
    parser.add_argument('--db', default=TEST_DB, help='Test database name')
    parser.add_argument('--report', action='store_true', help='Generate test report')
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if args.unit:
        tags = TEST_GROUPS['unit']
    elif args.integration:
        tags = TEST_GROUPS['integration']
    elif args.performance:
        tags = TEST_GROUPS['performance']
    elif args.controller:
        tags = TEST_GROUPS['controller']
    else:
        tags = TEST_GROUPS['all']
    
    if args.report:
        generate_test_report(tags, args.db)
        return 0
    
    return run_tests(tags, args.verbose, args.fail_fast, args.db)


if __name__ == '__main__':
    sys.exit(main())
