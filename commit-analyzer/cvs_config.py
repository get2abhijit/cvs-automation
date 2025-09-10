#!/usr/bin/env python3
"""
CVS Analyzer Configuration and Runner Script
Provides easy configuration and execution of CVS analysis
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import the main analyzer (assuming it's in the same directory)
try:
    from cvs_analyzer import CVSLogParser
except ImportError:
    print("Error: cvs_analyzer.py not found in the same directory!")
    sys.exit(1)

def parse_date(date_str):
    """Parse date string in various formats"""
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%d.%m.%Y', '%d/%m/%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}. Use format: YYYY-MM-DD")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze CVS commits and group related changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze last 30 days
  python cvs_config.py --days 30
  
  # Analyze specific date range
  python cvs_config.py --start 2024-01-01 --end 2024-02-01
  
  # Analyze specific author
  python cvs_config.py --author john.doe --days 60
  
  # Custom time window for grouping
  python cvs_config.py --days 14 --window 5
  
  # Specify output file
  python cvs_config.py --days 7 --output weekly_analysis.xlsx
        """
    )
    
    # Date range options
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--days', type=int, default=30,
                           help='Analyze last N days (default: 30)')
    date_group.add_argument('--start', type=str,
                           help='Start date (YYYY-MM-DD format)')
    
    parser.add_argument('--end', type=str,
                       help='End date (YYYY-MM-DD format, used with --start)')
    
    # Filter options
    parser.add_argument('--author', type=str,
                       help='Filter by specific author/username')
    
    # Analysis options
    parser.add_argument('--window', type=int, default=10,
                       help='Time window in minutes for grouping commits (default: 10)')
    
    # Output options
    parser.add_argument('--output', type=str,
                       help='Output Excel filename (default: auto-generated)')
    
    parser.add_argument('--path', type=str, default='.',
                       help='CVS repository path (default: current directory)')
    
    # Advanced options
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Calculate date range
    if args.start:
        try:
            start_date = parse_date(args.start)
            if args.end:
                end_date = parse_date(args.end)
            else:
                # end_date = datetime.now()
                end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        except ValueError as e:
            print(f"Date parsing error: {e}")
            return 1
    else:
        # Use days parameter
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    
    # Format dates for CVS
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    if args.verbose:
        print(f"Analysis Configuration:")
        print(f"  Date range: {start_str} to {end_str}")
        print(f"  Author filter: {args.author or 'All authors'}")
        print(f"  Time window: {args.window} minutes")
        print(f"  Repository path: {args.path}")
        print(f"  Output file: {args.output or 'Auto-generated'}")
        print()
    
    # Validate repository path
    repo_path = Path(args.path)
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {args.path}")
        return 1
    
    cvs_dir = repo_path / 'CVS'
    if not cvs_dir.exists():
        print(f"Warning: CVS directory not found in {args.path}")
        print("Make sure you're running this from within a CVS working directory")
    
    # Initialize analyzer
    analyzer = CVSLogParser(module_path=str(repo_path))
    
    # Run analysis
    try:
        result = analyzer.analyze_repository(
            start_date=start_str,
            end_date=end_str,
            author=args.author,
            time_window=args.window,
            output_file=args.output
        )
        
        if result:
            print(f"\n✓ Analysis completed successfully!")
            print(f"  Results saved to: {result}")
            return 0
        else:
            print("\n✗ Analysis failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)