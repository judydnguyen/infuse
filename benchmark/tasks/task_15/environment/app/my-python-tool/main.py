#!/usr/bin/env python3
"""
Main entry point for the Python tool.
"""

import sys
from utils.logger import setup_logger
from utils.config import load_config
from core.processor import DataProcessor
from core.validator import DataValidator
from cli.parser import parse_arguments

def main():
    """Main function to run the tool."""
    logger = setup_logger()
    logger.info("Starting Python Tool")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config_file)
    
    # Initialize processor
    processor = DataProcessor(config)
    
    # Initialize validator
    validator = DataValidator(config)
    
    # Process input file
    if args.input:
        logger.info(f"Processing input file: {args.input}")
        data = processor.load_data(args.input)
        
        # Validate data
        if validator.validate(data):
            logger.info("Data validation passed")
            result = processor.process(data)
            processor.save_result(result, args.output)
            logger.info(f"Result saved to: {args.output}")
        else:
            logger.error("Data validation failed")
            sys.exit(1)
    else:
        logger.error("No input file specified")
        sys.exit(1)

if __name__ == "__main__":
    main()
