import os
import sys
import json
from GMNS_Plus_Readiness_Validator import GMNSValidator, ReadinessLevel

def get_all_directories(root_path):
    """Recursively search for all directories under root_path, excluding .idea and other hidden directories."""
    dir_set = set()
    if os.path.exists(os.path.join(root_path, 'link.csv')):
        dir_set.add(root_path)
    for dirpath, dirnames, _ in os.walk(root_path):
        # Filter out hidden directories (starting with .)
        dirnames[:] = [d for d in dirnames if not (d.startswith('.') or d.startswith('_') or d.startswith('backup') or d.startswith('Accessibility_checking_tools'))]

        # Store absolute paths of directories
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            if os.path.exists(os.path.join(full_path,'link.csv')):
                dir_set.add(full_path)

    return dir_set

def find_file(pattern, default_name, working_path):
    """Find a file in the given working directory based on a pattern."""
    for filename in os.listdir(working_path):
        if pattern in filename:
            return os.path.join(working_path, filename)
    return os.path.join(working_path, default_name) if os.path.exists(
        os.path.join(working_path, default_name)) else None


def ReadinessChecking(working_path):
    """Main function to run the GMNS validator with minimal parameters."""
    print("GMNS Network Validator")
    print("=========================")

    print(f"Working directory: {working_path}")

    # Parse command line arguments for validation level
    level = 7  # Default level is 7
    if len(sys.argv) > 1:
        try:
            level_arg = int(sys.argv[1])
            if 1 <= level_arg <= 7:
                level = level_arg
            else:
                print(f"Invalid level: {level_arg}. Using default level 7.")
        except ValueError:
            print(f"Invalid level argument: {sys.argv[1]}. Using default level 7.")

    # Auto-detect files in the working directory
    node_file = find_file("node", "node.csv", working_path)
    link_file = find_file("link", "link.csv", working_path)
    demand_file = find_file("demand", "demand.csv", working_path)

    # Validate that required files exist
    if not node_file:
        print("Warning: No node file found. Please ensure a CSV file with 'node' in the name exists if possible.")
        # return 1

    if not link_file:
        print("Error: No link file found. Please ensure a CSV file with 'link' in the name exists.")
        return 1

    print(f"Using node file: {node_file}")
    print(f"Using link file: {link_file}")
    if demand_file:
        print(f"Using demand file: {demand_file}")
    else:
        print("No demand file found. Continuing without demand validation.")

    print(f"Validation level: {level}")

    try:
        # Initialize validator
        validator = GMNSValidator(
            node_file=node_file,
            link_file=link_file,
            demand_file=demand_file)

        # Run validation at specified level
        readiness_level = ReadinessLevel(level)
        print(f"\nRunning validation at Readiness Level {level}...")
        validator.validate(readiness_level)

        # Print report to console
        validator.print_report()

        # Save report to JSON file automatically
        output_file = os.path.join(working_path, "validation_report.json")
        report = validator.generate_report()
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to {output_file}")
        except Exception as e:
            print(f"Warning: Could not save report to file: {e}")

        # Get error count
        error_count = report['summary']['errors']

        # Return non-zero exit code if errors were found
        return 1 if error_count > 0 else 0

    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    subdirectories = get_all_directories('.')
    #subdirectories = get_all_directories(r'16_Sydney')
    print("Subdirectories:")
    for subdir in subdirectories:
        print(subdir)
        ReadinessChecking(subdir)
