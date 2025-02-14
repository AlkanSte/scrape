import sys
from pathlib import Path
import re

def create_safe_filename(search_string: str) -> str:
    """Create a safe filename by removing/replacing unsafe characters."""
    # Replace unsafe characters with underscores
    safe_string = re.sub(r'[=\s/\\<>:"|?*]', '_', search_string)
    return safe_string

def search_in_file(file_path: str, search_string: str):
    """
    Search for string in file and write matches to output file.
    
    Args:
        file_path: Path to log file
        search_string: String to search for
    """
    # Create safe output file name
    safe_search = create_safe_filename(search_string)
    output_file = f"search_results_{Path(file_path).stem}_{safe_search}.txt"
    print(f"Will write results to: {output_file}")
    
    try:
        matches = 0
        print(f"Searching for '{search_string}' in {file_path}")
        
        # Open output file once, outside the encoding loop
        with open(output_file, 'w', encoding='utf-8') as out:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Remove ANSI color codes
                    clean_line = re.sub(r'\x1b\[\d+m', '', line)
                    if search_string in clean_line:
                        out.write(f"{line_num}ζ{clean_line}")
                        matches += 1
                        if matches <= 3:  # Print first 3 matches for debugging
                            print(f"Found match at line {line_num}: {clean_line.strip()}")
            
            print(f"Found {matches} matches")
            if matches > 0:
                print(f"Results written to: {output_file}")
            else:
                print("No matches found")
                        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise  # Add this to see the full error trace

def main():
    # Check arguments
    if len(sys.argv) != 3:
        print("Usage: python search_logs.py <file_path> <search_string>")
        print("Example: python search_logs.py client_log/client_UID_199.log 'Sending query'")
        sys.exit(1)
        
    file_path = sys.argv[1]
    search_string = sys.argv[2]
    
    search_in_file(file_path, search_string)

if __name__ == "__main__":
    main() 