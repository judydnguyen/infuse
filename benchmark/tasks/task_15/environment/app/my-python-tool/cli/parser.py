"""
Command line argument parser module.
"""

import argparse

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Python tool for data processing and validation',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='Input file path (JSON or CSV)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.json',
        help='Output file path (default: output.json)'
    )
    
    parser.add_argument(
        '-c', '--config',
        dest='config_file',
        type=str,
        default=None,
        help='Configuration file path (optional)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()
