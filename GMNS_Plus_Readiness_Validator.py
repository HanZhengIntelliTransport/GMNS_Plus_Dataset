import os
import pandas as pd
import json
import math
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from sklearn.metrics import r2_score
import shutil
import subprocess
import time
import DTALite

flag_Run_Accessibility_Checking=True
flag_Run_exe=False
template_path='GMNS_Tools/Accessibility_checking_tools'

def wait_for_file(file_path, timeout=60, check_interval=1):
    """
    Wait for a file to be created within a specified timeout period.

    Parameters:
    - file_path (str): The full path of the expected output file.
    - timeout (int): Maximum time (in seconds) to wait for the file. Default is 60 seconds.
    - check_interval (int): Interval (in seconds) between checks. Default is 1 second.

    Returns:
    - bool: True if the file is found within the timeout, False otherwise.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            print(f"File found: {file_path}")
            return True
        time.sleep(check_interval)

    print(f"Timeout reached. File not found: {file_path}")
    return False

def use_python_DTALite(working_path,template_path):
    csv_file = "settings.csv"
    NEXTA_file = "NEXTA.exe"
    csv_src = os.path.join(template_path, csv_file)
    NEXTA_src = os.path.join(template_path, NEXTA_file)
    csv_dest = os.path.join(working_path, csv_file)
    NEXTA_dest = os.path.join(working_path, NEXTA_file)
    shutil.copy(NEXTA_src, NEXTA_dest)
    shutil.copy(csv_src, csv_dest)

    print(f"Copied {csv_file} and {NEXTA_file} to {working_path}")
    original_path = os.getcwd()  # Save the current working directory
    try:
        os.chdir(working_path)   # Change to the desired working directory
        DTALite.assignment()     # Run the assignment in the target directory
    finally:
        os.chdir(original_path)  # Restore the original working directory
    return


def copy_and_run_exe(working_path, template_path):
    """Copy a specific .exe and .csv file from template_path to working_path and run the .exe, showing real-time output."""
    try:
        # Convert to absolute paths
        working_path = os.path.abspath(working_path)
        template_path = os.path.abspath(template_path)

        # Ensure directories exist
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template path does not exist: {template_path}")
        if not os.path.exists(working_path):
            os.makedirs(working_path, exist_ok=True)

        print(f"Template path: {template_path}")
        print(f"Working path: {working_path}")

        # Specify the .exe and .csv files
        DTALite_file = "TAPLite_0321_2025.exe"
        NEXTA_file= "NEXTA.exe"
        csv_file = "settings.csv"
        #mode_csv_file = "mode_type.csv"

        DTALite_src = os.path.join(template_path, DTALite_file)
        NEXTA_src = os.path.join(template_path, NEXTA_file)
        csv_src = os.path.join(template_path, csv_file)
        #mode_csv_src = os.path.join(template_path, mode_csv_file)

        if not os.path.exists(DTALite_src) or not os.path.exists(csv_src) or not os.path.exists(NEXTA_src):
        #if not os.path.exists(DTALite_src) or not os.path.exists(csv_src) or not os.path.exists(NEXTA_src) or not os.path.exists(mode_csv_src):
            raise FileNotFoundError("The required .exe or .csv file is missing in the template directory.")

        # Copy files to working_path
        DTALite_dest = os.path.join(working_path, DTALite_file)
        NEXTA_dest=os.path.join(working_path, NEXTA_file)
        csv_dest = os.path.join(working_path, csv_file)
        #mode_csv_dest = os.path.join(working_path, mode_csv_file)

        shutil.copy(DTALite_src, DTALite_dest)
        shutil.copy(NEXTA_src, NEXTA_dest)
        shutil.copy(csv_src, csv_dest)
        #shutil.copy(mode_csv_src, mode_csv_dest)

        print(f"Copied {DTALite_file},{NEXTA_file} and {csv_file} to {working_path}")

        # Run the .exe file with real-time output
        process = subprocess.Popen(
            [DTALite_dest], cwd=working_path, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        for line in iter(process.stdout.readline, ''):
            print(line, end='')  # Print real-time output

        process.stdout.close()
        process.wait()

        print(f"Executed {DTALite_file} in {working_path}")

    except Exception as e:
        print(f"Error: {e}")

class ReadinessLevel(Enum):
    """Readiness levels for networks based on GMNS standards."""
    LEVEL_1 = 1  # Basic validations (node, link files exist and basic structure check)
    LEVEL_2 = 2  # Demand and zone consistency
    LEVEL_3 = 3  # Network attributes like free flow speeds, capacities
    LEVEL_4 = 4  # Single mode configuration (setings.csv and mode_type.csv) validation
    LEVEL_5 = 5  # pre-ODME observed volume checks
    LEVEL_6 = 6  # Evaluating overall network accessibility via origin/destination reachability, average travel times, and free-flow vs. congested conditions.
    LEVEL_7 = 7  # Comparing reference volumes with assigned volumes (using R²), and identifying outliers in the assignment.
    LEVEL_8 = 8  # Verifying that the adjusted demands match target demands, ensuring that high-demand OD pairs have been assigned feasible paths, and checking for significant deviations in travel times and volumes.

class ValidationStatus(Enum):
    """Status of validation result."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"

class ValidationResult:
    """Captures details about a single validation check result."""
    def __init__(self, status: ValidationStatus, message: str, 
                 field: Optional[str] = None, details: Optional[Dict] = None):
        self.status = status
        self.message = message
        self.field = field
        self.details = details if details else {}
    
    def __str__(self):
        prefix = f"[{self.status.value.upper()}]"
        field_info = f" Field: {self.field}" if self.field else ""
        return f"{prefix}{field_info} - {self.message}"

class GMNSValidator:
    """
    A comprehensive validator framework for networks based on GMNS standards.
    """
    # Constants for unit conversions
    KMH_TO_MS = 1000 / 3600  # km/h to m/s conversion
    MPH_TO_KMH = 1.60934  # mph to km/h conversion
    MI_TO_M = 1609.34  # miles to meters conversion
    
    # Node field definitions with types and validation rules
    NODE_FIELDS = {
        "node_id": {
            "type": "int", 
            "required": True,
            "description": "Unique identifier for each node"
        },
        "zone_id": {
            "type": "int", 
            "required": True,
            "description": "Zone identifier (node_id == zone_id indicates a centroid)"
        },
        "x_coord": {
            "type": "float", 
            "required": True,
            "description": "X-coordinate (longitude)"
        },
        "y_coord": {
            "type": "float", 
            "required": True,
            "description": "Y-coordinate (latitude)"
        },
        "district_id": {
            "type": "float", 
            "required": False,
            "description": "Identifier for district/region grouping"
        },
        # Additional optional fields
        "elevation": {
            "type": "float", 
            "required": False,
            "description": "Node elevation in meters"
        },
        "ctrl_type": {
            "type": "int", 
            "required": False,
            "description": "Control type (e.g., 0-unsignalized, 1-signalized)"
        },
        "name": {
            "type": "str", 
            "required": False,
            "description": "Node name or description"
        },
        "modes": {
            "type": "str", 
            "required": False,
            "description": "Supported travel modes"
        }
    }
    
    # Link field definitions with types and validation rules
    LINK_FIELDS = {
        "link_id": {
            "type": "int", 
            "required": True,
            "description": "Unique identifier for each link"
        },
        "from_node_id": {
            "type": "int", 
            "required": True,
            "description": "Node ID for the origin node"
        },
        "to_node_id": {
            "type": "int", 
            "required": True,
            "description": "Node ID for the destination node"
        },
        "length": {
            "type": "float", 
            "required": True,
            "unit": "meters",
            "description": "Link length in meters"
        },
        "vdf_length_mi": {
            "type": "float", 
            "required": False,
            "unit": "miles",
            "description": "Link length in miles for VDF calculation"
        },
        "lanes": {
            "type": "int", 
            "required": True,
            "description": "Number of lanes"
        },
        "capacity": {
            "type": "float", 
            "required": True,
            "unit": "vehicles/hour/lane",
            "description": "Link capacity in vehicles per hour per lane"
        },
        "free_speed": {
            "type": "float", 
            "required": True,
            "unit": "km/h",
            "description": "Free-flow speed in km/h"
        },
        "vdf_free_speed_mph": {
            "type": "float", 
            "required": False,
            "unit": "mph",
            "description": "Free-flow speed in mph for VDF calculation"
        },
        "link_type": {
            "type": "int", 
            "required": True,
            "description": "Link type code"
        },
        "dir_flag": {
            "type": "int", 
            "required": True,
            "description": "Direction flag (1-one way, 0-two way)"
        },
        "vdf_alpha": {
            "type": "float", 
            "required": True,
            "description": "Volume delay function alpha parameter"
        },
        "vdf_beta": {
            "type": "float", 
            "required": True,
            "description": "Volume delay function beta parameter"
        },
        "vdf_plf": {
            "type": "float", 
            "required": True,
            "description": "Volume delay function plf parameter"
        },
        "vdf_fftt": {
            "type": "float", 
            "required": False,
            "unit": "minutes",
            "description": "Free flow travel time in minutes for VDF calculation"
        },
        "ref_volume": {
            "type": "float", 
            "required": False,
            "description": "Reference volume for validation from standard assignemnt results"
        },
        "obs_volume": {
            "type": "float", 
            "required": False,
            "description": "Observed volume for validation from sensor observation for mode type 1"
        },
        "obs_volume_sov": {
            "type": "float", 
            "required": False,
            "description": "Observed volume for validation from sensor observation for sov mode"
        },
        "obs_volume_truck": {
            "type": "float", 
            "required": False,
            "description": "Observed volume for validation from sensor observation for truck mode"
        },
        "base_volume": {
            "type": "float", 
            "required": False,
            "description": "Base volume for the link"
        },
        "base_vol_auto": {
            "type": "float", 
            "required": False,
            "description": "Base volume for automobile mode"
        },
        "background_volume": {
            "type": "float", 
            "required": False,
            "description": "Background volume for the link"
        },
        "vdf_toll": {
            "type": "float", 
            "required": False,
            "description": "Toll amount for auto mode in VDF calculation (mode type 1) for only one mode"
        },
        "vdf_toll_sov": {
            "type": "float", 
            "required": False,
            "description": "Toll amount for sov mode in VDF calculation"
        },
        "vdf_toll_truck": {
            "type": "float", 
            "required": False,
            "description": "Toll amount for truck mode in VDF calculation"
        },
        "geometry": {
            "type": "str", 
            "required": False,
            "description": "Geometry data for the link (often in WKT format)"
        }
    }
    
    # Demand file fields
    DEMAND_FIELDS = {
        "o_zone_id": {
            "type": "int", 
            "required": True,
            "description": "Origin zone ID"
        },
        "d_zone_id": {
            "type": "int", 
            "required": True,
            "description": "Destination zone ID"
        },
        "volume": {
            "type": "float", 
            "required": True,
            "description": "Travel demand volume"
        },
        "time_period": {
            "type": "str", 
            "required": False,
            "description": "Time period for the demand (e.g., AM, PM)"
        },
        "mode": {
            "type": "str", 
            "required": False,
            "description": "Travel mode for the demand"
        }
    }
    
    def __init__(self, node_file: str, link_file: str, demand_file: Optional[str] = None,
                 config_file: Optional[str] = None):
        """
        Initialize the validator with required data files.
        
        Args:
            node_file: Path to the node CSV file
            link_file: Path to the link CSV file
            demand_file: Optional path to the demand CSV file
            config_file: Optional path to configuration JSON file
        """
        self.node_file = node_file
        self.link_file = link_file
        self.demand_file = demand_file
        self.working_path=os.path.dirname(link_file)
        self.config_file = config_file
        
        # Load data files
        if (node_file != None):
            self.node_df = self._load_csv(node_file)
        else:
            self.node_df = None
        self.link_df = self._load_csv(link_file)
        self.demand_df = self._load_csv(demand_file) if demand_file else None
        self.config = self._load_config(config_file) if config_file else None
        
        # Initialize result storage
        self.results = []
        
        # Initialize validation tracking
        self._validated_levels = set()

    
    def _load_csv(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file into a pandas DataFrame."""
        try:
            df = pd.read_csv(file_path, low_memory=False)
            # Convert all column names to lowercase for consistency
            df.columns = [col.lower() for col in df.columns]
            return df
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Failed to load {file_path}: {str(e)}"
                )
            )
            return pd.DataFrame()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from a JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Failed to load config from {config_file}: {str(e)}"
                )
            )
            return {}
    
    def validate(self, level: ReadinessLevel = ReadinessLevel.LEVEL_1) -> Dict:
        """
        Run all validations up to and including the specified readiness level.
        
        Args:
            level: The readiness level to validate up to
            
        Returns:
            A dictionary with validation results
        """
        # Clear previous results
        self.results = []
        
        # Start with basic file existence validation
        self._validate_file_existence()
        
        # Run validations based on readiness level
        if level.value == ReadinessLevel.LEVEL_1.value:
            self._validate_level_1()
        
        if level.value == ReadinessLevel.LEVEL_2.value:
            self._validate_level_2()
            
        if level.value == ReadinessLevel.LEVEL_3.value:
            self._validate_level_3()
            
        if level.value == ReadinessLevel.LEVEL_4.value:
            self._validate_level_4()
            
        if level.value == ReadinessLevel.LEVEL_5.value:
            self._validate_level_5()
            
        if level.value == ReadinessLevel.LEVEL_6.value:
            self._validate_level_6()
        
        if level.value == ReadinessLevel.LEVEL_7.value:
            self._validate_level_7()
            
        if level.value == ReadinessLevel.LEVEL_8.value:
            self._validate_level_8()

        return self.generate_report()
    
    def _validate_file_existence(self):
        """Validate that required files exist and are not empty."""
        if self.node_df is not None and self.node_df.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Node file is empty or couldn't be loaded: {self.node_file}"
                )
            )
        
        if self.link_df.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Link file is empty or couldn't be loaded: {self.link_file}"
                )
            )
    
    def _validate_level_1(self):
        """
        Level 1: Basic validations for node and link files.
        """
        # Skip if files don't exist and self.node_df.empty
        if self.node_df is None  or self.link_df.empty:
            return
        
        # Check required columns
        self._check_required_fields(self.node_df, self.NODE_FIELDS, "node")
        self._check_required_fields(self.link_df, self.LINK_FIELDS, "link")
        
        # Check data types 
        self._check_field_types(self.node_df, self.NODE_FIELDS, "node")
        self._check_field_types(self.link_df, self.LINK_FIELDS, "link")
        
        # Validate forward-star structure
        self._check_sorted_nodes()
        self._check_sorted_links()
        
        # Check that link endpoints exist in nodes
        self._validate_link_endpoints()
        
        # Check for duplicates
        self._check_duplicates(self.node_df, "node_id", "node")
        self._check_duplicates(self.link_df, "link_id", "link")
    
    def _validate_level_2(self):
        """
        Level 2: Demand and zone consistency validations.
        """
        # First run all level 1 validations
        self._validate_level_1()
        
        # Check zone centroids in node file
        self._check_zone_centroid_structure()
        
        # Check for connector links
        self._validate_connectors()
        
        # Check zone IDs are consistent
        self._validate_zone_consistency()
        
        # Validate demand file format and content
        if self.demand_df is not None and not self.demand_df.empty:
            # First validate the demand file format
            self._validate_demand_format()
            
            # Then check required fields and validate content
            self._check_required_fields(self.demand_df, self.DEMAND_FIELDS, "demand")
            self._validate_demand_zones()
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "Demand file not provided or empty. Skipping demand validations.",
                    details={"level": 2}
                )
            )
    
    def _validate_level_3(self):
        """
        Level 3: Network attribute validations.
        """
        # Check for VDF parameters
        self._validate_vdf_parameters()
        
        # Validate speed and length units
        self._validate_speed_units()
        self._validate_length_units()
        
        # Validate capacity values
        self._validate_capacity_values()
        
        # Validate unit conversions between fields
        self._validate_unit_consistency()
        self._validate_level_2()
    
    def _validate_level_4(self):
        """
        Level 4: Single mode validation.
        """
        # Check for mode consistency
        self._validate_config_files()
        self._validate_level_3()
    
    def _validate_level_5(self):
        """
        Level 5: Observed volume checks and ODME validation.
        """
        # First run checks from previous levels
        self._validate_level_4()
        
        # Check for observed volumes
        self._validate_observed_volumes()
        
        # Validate ODME settings and data
        self._validate_odme_configuration()
    
    def _validate_level_6(self):
        """
        Level 6: Accessibility checks
        - Verifies network connectivity and accessibility measures
        - Checks if OD pairs in demand files have feasible paths
        - Identifies problematic origin-destination connections
        """
        # Check if this level has already been validated
        if ReadinessLevel.LEVEL_6 in self._validated_levels:
            return
            
        # First run all level 5 validations
        self._validate_level_5()

        if flag_Run_Accessibility_Checking:
            if flag_Run_exe:
                copy_and_run_exe(working_path=self.working_path,template_path=template_path)
            else:
                use_python_DTALite(working_path=self.working_path,template_path=template_path)

        od_performance_file=os.path.join(self.working_path,'od_performance.csv')
        if wait_for_file(od_performance_file, timeout=120, check_interval=1):
            self._validate_od_connectivity(od_performance_file)
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "od_performance.csv not found. Cannot perform accessibility validation.",
                    field="accessibility"
                )
            )

        # Load route assignment file if available
        route_assignment_file = self._find_output_file('route_assignment.csv')
        if not route_assignment_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    "route_assignment.csv not found. Will only use od_performance.csv for accessibility checks.",
                    field="accessibility"
                )
            )
        else:
            # Validate route assignments
            self._validate_route_assignments(route_assignment_file)
        
        # Mark this level as validated
        self._validated_levels.add(ReadinessLevel.LEVEL_6)



    def validate_traffic_assignment(self):
        """
        Validates traffic assignment by checking link.csv and link_performance.csv,
        extracting reference and observed volumes, and computing R^2.

        :param results: A list to append validation results (ValidationResult instances expected)
        """
        link_file = os.path.join(self.working_path,"link.csv")
        link_performance_file =os.path.join(self.working_path,"link_performance.csv")

        # Check if link.csv exists
        if not os.path.exists(link_file):
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "link.csv not found. Cannot perform validation.",
                    field="link"
                )
            )
            return

        # Load link.csv and check for ref_volume
        df_link = pd.read_csv(link_file)
        if "ref_volume" not in df_link.columns or df_link["ref_volume"].isna().all():
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "Column 'ref_volume' not found or empty in link.csv. Cannot perform ref_volume and volume comparison.",
                    field="ref_volume"
                )
            )
            return

        ref_volume = df_link["ref_volume"].dropna()

        # Success message for link.csv validation
        self.results.append(
            ValidationResult(
                ValidationStatus.SUCCESS,
                "ref_volume imported successfully",
                field="ref_volume"
            )
        )

        # Check if link_performance.csv exists
        if not os.path.exists(link_performance_file):
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "link_performance.csv not found. Cannot perform ref_volume and volume comparison.",
                    field="link_performance"
                )
            )
            return

        # Load link_performance.csv and check for volume
        df_performance = pd.read_csv(link_performance_file)
        if "volume" not in df_performance.columns or df_performance["volume"].isna().all():
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "Column 'volume' not found or empty in link_performance.csv. Cannot perform ref_volume and volume comparison.",
                    field="volume"
                )
            )
            return

        volume = df_performance["volume"].dropna()

        # Ensure both ref_volume and volume have the same length for comparison
        min_length = min(len(ref_volume), len(volume))
        ref_volume = ref_volume[:min_length]
        volume = volume[:min_length]

        # Compute R^2
        r2 = r2_score(ref_volume, volume)

        self.results.append(
            ValidationResult(
                ValidationStatus.SUCCESS,
                f"R^2 value computed: {r2:.4f}. Comparison successful.",
                field="r2_score"
            )
        )

    def _validate_level_7(self):
        """
        Level 7: Traffic assignment validation
        """
        # First run all level 6 validations
        self._validate_level_6()
        
        # Load link performance file if available
        link_performance_file = self._find_output_file("link_performance.csv")
        if not link_performance_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "link_performance.csv not found. Cannot perform assignment validation.",
                    field="assignment"
                )
            )
        else:
            # Validate link performance
            self._validate_link_performance(link_performance_file)
            
            # Add success message after link performance validation completes
            self.results.append(
                ValidationResult(
                    ValidationStatus.SUCCESS,
                    "Link performance validation completed successfully with reasonable metrics",
                    field="assignment"
                )
            )

        self.validate_traffic_assignment()

        # Load route assignment file if available
        route_assignment_file = self._find_output_file("route_assignment.csv")
        if not route_assignment_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    "route_assignment.csv not found. Will only use link_performance.csv for assignment checks.",
                    field="assignment"
                )
            )
        else:
            # Validate route assignments
            self._validate_route_assignments(route_assignment_file)
            
            # Add success message after route assignment validation completes
            self.results.append(
                ValidationResult(
                    ValidationStatus.SUCCESS,
                    "Route assignment validation completed successfully with proper path distributions",
                    field="route_assignment"
                )
            )
        
        # Add overall success message for Level 7
        self.results.append(
            ValidationResult(
                ValidationStatus.SUCCESS,
                "Traffic assignment validation (Level 7) completed successfully",
                field="level_7"
            )
        )

    def _validate_level_8(self):
        """
        Level 8: Post-OD Assignment Validation
        """
        # First run all level 7 validations
        self._validate_level_7()

        # Load demand file and check existence
        demand_file = self._find_output_file("demand.csv")
        if not demand_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "demand.csv not found. Cannot perform post-OD assignment validation.",
                    field="od_assignment"
                )
            )
            return

        # Load and process demand data
        demand_df = pd.read_csv(demand_file)
        if not {'o_zone_id', 'd_zone_id', 'volume'}.issubset(demand_df.columns):
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "demand.csv is missing required columns (o_zone_id, d_zone_id, volume).",
                    field="od_assignment"
                )
            )
            return

        # Sort demand data by volume (descending) and select top-k OD pairs
        k = 10  # Number of top OD pairs to analyze
        top_od_pairs = demand_df.nlargest(k, 'volume')[['o_zone_id', 'd_zone_id', 'volume']]

        # Load OD performance file and check existence
        od_performance_file = self._find_output_file("od_performance.csv")
        if not od_performance_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "od_performance.csv not found. Cannot compare assigned volumes.",
                    field="od_assignment"
                )
            )
        else:
            # Load and process OD performance data
            od_performance_df = pd.read_csv(od_performance_file)
            if not {'o_zone_id', 'd_zone_id', 'assigned_volume'}.issubset(od_performance_df.columns):
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        "od_performance.csv is missing required columns (o_zone_id, d_zone_id, assigned_volume).",
                        field="od_assignment"
                    )
                )
            else:
                # Merge to compare target vs assigned volume
                merged_df = top_od_pairs.merge(
                    od_performance_df, on=['o_zone_id', 'd_zone_id'], how='left'
                )
                merged_df['volume_difference'] = merged_df['volume'] - merged_df['assigned_volume']

                # Log any significant discrepancies
                for _, row in merged_df.iterrows():
                    if abs(row['volume_difference']) > 0.1 * row['volume']:  # Example threshold of 10%
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Significant volume deviation for OD ({row['o_zone_id']} -> {row['d_zone_id']}): "
                                f"Expected {row['volume']}, Assigned {row['assigned_volume']}, Difference {row['volume_difference']}",
                                field="od_assignment"
                            )
                        )

        # Load route assignment file and check existence
        route_assignment_file = self._find_output_file("route_assignment.csv")
        if not route_assignment_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "route_assignment.csv not found. Cannot analyze travel time for top OD pairs.",
                    field="route_assignment"
                )
            )
        else:
            # Load and process route assignment data
            route_assignment_df = pd.read_csv(route_assignment_file)
            if not {'o_zone_id', 'd_zone_id', 'travel_time', 'volume'}.issubset(route_assignment_df.columns):
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        "route_assignment.csv is missing required columns (o_zone_id, d_zone_id, travel_time, volume).",
                        field="route_assignment"
                    )
                )
            else:
                # Merge with top OD pairs and analyze travel times
                travel_time_df = top_od_pairs.merge(
                    route_assignment_df, on=['o_zone_id', 'd_zone_id'], how='left'
                )

                # Define a reasonable travel time range based on percentiles
                valid_time_range = (
                    route_assignment_df['travel_time'].quantile(0.05),
                    route_assignment_df['travel_time'].quantile(0.95)
                )

                for _, row in travel_time_df.iterrows():
                    if row['travel_time'] < valid_time_range[0] or row['travel_time'] > valid_time_range[1]:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Unusual travel time for OD ({row['o_zone_id']} -> {row['d_zone_id']}): "
                                f"Travel time {row['travel_time']} out of range {valid_time_range}",
                                field="route_assignment"
                            )
                        )

        # Add overall success message for Level 8
        self.results.append(
            ValidationResult(
                ValidationStatus.SUCCESS,
                "Post-OD assignment validation (Level 8) completed successfully",
                field="level_8"
            )
        )

    def _validate_link_performance(self, link_performance_file):
        """
        Validate link performance data from link_performance.csv.
        - Check assigned volumes
        - Validate VHT and VMT
        - Compare with reference/observed volumes if available
        - Check congestion parameters (P, doc)
        """
        try:
            # Load link performance data
            link_perf_df = pd.read_csv(link_performance_file)
            
            # Check for required columns based on your file structure
            required_columns = ["link_id", "volume", "travel_time"]
            
            missing_columns = [col for col in required_columns if col not in link_perf_df.columns]
            
            if missing_columns:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing required columns in link_performance.csv: {', '.join(missing_columns)}",
                        field="assignment",
                        details={"missing_columns": missing_columns}
                    )
                )
                return
                    
            # Calculate basic volume statistics
            total_volume = link_perf_df["volume"].sum()
            total_vmt = link_perf_df["VMT"].sum() if "VMT" in link_perf_df.columns else 0
            total_vht = link_perf_df["VHT"].sum() if "VHT" in link_perf_df.columns else 0
            
            # Calculate network average speed
            if total_vht > 0:
                avg_speed = total_vmt / total_vht  # miles per hour
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Assignment metrics: Total volume = {total_volume:.1f}, VMT = {total_vmt:.1f} vehicle-miles, VHT = {total_vht:.1f} vehicle-hours, Avg speed = {avg_speed:.1f} mph",
                        field="assignment",
                        details={
                            "total_volume": float(total_volume),
                            "total_vmt": float(total_vmt),
                            "total_vht": float(total_vht),
                            "avg_speed": float(avg_speed)
                        }
                    )
                )
                
                # Check for reasonable average speed
                if avg_speed < 5:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Average network speed ({avg_speed:.1f} mph) is unreasonably low",
                            field="assignment",
                            details={"avg_speed": float(avg_speed)}
                        )
                    )
                elif avg_speed > 70:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Average network speed ({avg_speed:.1f} mph) is unreasonably high",
                            field="assignment",
                            details={"avg_speed": float(avg_speed)}
                        )
                    )
            
            # Check if speed_mph and speed_kmph columns exist
            if "speed_mph" in link_perf_df.columns:
                # Report link speed statistics
                avg_link_speed_mph = link_perf_df["speed_mph"].mean()
                min_link_speed_mph = link_perf_df["speed_mph"].min()
                max_link_speed_mph = link_perf_df["speed_mph"].max()
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Link speed statistics: Average = {avg_link_speed_mph:.1f} mph, Range = {min_link_speed_mph:.1f} - {max_link_speed_mph:.1f} mph",
                        field="assignment",
                        details={
                            "avg_link_speed_mph": float(avg_link_speed_mph),
                            "min_link_speed_mph": float(min_link_speed_mph),
                            "max_link_speed_mph": float(max_link_speed_mph)
                        }
                    )
                )
                
                # Check for links with very low speeds
                very_slow_links = link_perf_df[link_perf_df["speed_mph"] < 5]
                if not very_slow_links.empty:
                    very_slow_count = len(very_slow_links)
                    very_slow_percent = 100 * very_slow_count / len(link_perf_df)
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {very_slow_count} links ({very_slow_percent:.1f}%) with very low speeds (<5 mph)",
                            field="assignment",
                            details={
                                "very_slow_count": very_slow_count,
                                "very_slow_percent": float(very_slow_percent)
                            }
                        )
                    )
            
            # Check against observed volumes if available
            if "obs_volume" in link_perf_df.columns:
                self._compare_assigned_observed_volumes(link_perf_df)
            
            # NEW: Check against reference volumes if available
            if "ref_volume" in link_perf_df.columns:
                self._compare_assigned_reference_volumes(link_perf_df)
            
            # NEW: Check doc parameter (should be between 0 and 4)
            if "doc" in link_perf_df.columns:
                invalid_doc = link_perf_df[(link_perf_df["doc"] < 0) | (link_perf_df["doc"] > 4)]
                if not invalid_doc.empty:
                    invalid_doc_count = len(invalid_doc)
                    invalid_doc_percent = 100 * invalid_doc_count / len(link_perf_df)
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {invalid_doc_count} links ({invalid_doc_percent:.1f}%) with invalid doc values (<0 or >4)",
                            field="assignment",
                            details={
                                "invalid_doc_count": invalid_doc_count,
                                "invalid_doc_percent": float(invalid_doc_percent),
                                "example_links": invalid_doc["link_id"].head(5).tolist() if "link_id" in invalid_doc.columns else []
                            }
                        )
                    )
                else:
                    # Report doc statistics
                    avg_doc = link_perf_df["doc"].mean()
                    max_doc = link_perf_df["doc"].max()
                    
                    # Categorize doc values
                    severe_congestion = link_perf_df[link_perf_df["doc"] > 2]
                    severe_count = len(severe_congestion)
                    severe_percent = 100 * severe_count / len(link_perf_df)
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Doc statistics: Average = {avg_doc:.2f}, Max = {max_doc:.2f}, {severe_percent:.1f}% of links have severe congestion (doc > 2)",
                            field="assignment",
                            details={
                                "avg_doc": float(avg_doc),
                                "max_doc": float(max_doc),
                                "severe_congestion_percent": float(severe_percent)
                            }
                        )
                    )
            
            # NEW: Check P parameter (congestion duration - should be less than 5 hours)
            if "P" in link_perf_df.columns:
                # Filter out rows with missing P values
                valid_p = link_perf_df[link_perf_df["P"].notna()]
                
                if not valid_p.empty:
                    high_p = valid_p[valid_p["P"] > 5]
                    if not high_p.empty:
                        high_p_count = len(high_p)
                        high_p_percent = 100 * high_p_count / len(valid_p)
                        
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Found {high_p_count} links ({high_p_percent:.1f}%) with excessive congestion duration (P > 5 hours)",
                                field="assignment",
                                details={
                                    "high_p_count": high_p_count,
                                    "high_p_percent": float(high_p_percent),
                                    "example_links": high_p["link_id"].head(5).tolist() if "link_id" in high_p.columns else []
                                }
                            )
                        )
                    
                    # Report P statistics
                    avg_p = valid_p["P"].mean()
                    max_p = valid_p["P"].max()
                    non_zero_p = valid_p[valid_p["P"] > 0]
                    non_zero_percent = 100 * len(non_zero_p) / len(valid_p)
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Congestion duration statistics: Average = {avg_p:.2f} hours, Max = {max_p:.2f} hours, {non_zero_percent:.1f}% of links have congestion (P > 0)",
                            field="assignment",
                            details={
                                "avg_p": float(avg_p),
                                "max_p": float(max_p),
                                "congested_links_percent": float(non_zero_percent)
                            }
                        )
                    )
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error validating link performance: {str(e)}",
                    field="assignment"
                )
            )
    def _compare_assigned_observed_volumes(self, link_perf_df):
        """
        Compare assigned volumes with reference volumes.
        Calculate R^2, RMSE, and percentage error metrics.
        """
        try:
            # Filter to links with valid reference volumes
            volume_comparison = link_perf_df[
                (link_perf_df["obs_volume"].notna()) &
                (link_perf_df["obs_volume"] > 0) &
                (link_perf_df["volume"].notna())
            ]

            if len(volume_comparison) == 0:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        "No links with valid reference volumes found for comparison.",
                        field="reference_volume"
                    )
                )
                return

            # Calculate comparison metrics
            n_points = len(volume_comparison)

            # Calculate correlation and R^2
            assigned = volume_comparison["volume"].values
            reference = volume_comparison["obs_volume"].values

            # Calculate means
            assigned_mean = assigned.mean()
            reference_mean = reference.mean()

            # Calculate correlation numerator and denominator
            numerator = sum((assigned[i] - assigned_mean) * (reference[i] - reference_mean) for i in range(n_points))
            denominator = math.sqrt(
                sum((assigned[i] - assigned_mean)**2 for i in range(n_points)) *
                sum((reference[i] - reference_mean)**2 for i in range(n_points))
            )

            correlation = numerator / denominator if denominator != 0 else 0
            r_squared = correlation ** 2

            # Calculate RMSE
            sq_errors = [(assigned[i] - reference[i])**2 for i in range(n_points)]
            rmse = math.sqrt(sum(sq_errors) / n_points)

            # Calculate mean absolute percentage error (MAPE)
            percent_errors = [abs(assigned[i] - reference[i]) / reference[i] for i in range(n_points)]
            mape = 100 * sum(percent_errors) / n_points

            # Calculate GEH statistic for traffic volumes
            geh_values = [
                math.sqrt(2 * (assigned[i] - reference[i])**2 / (assigned[i] + reference[i]))
                if (assigned[i] + reference[i]) > 0 else 0
                for i in range(n_points)
            ]

            geh_under_5_count = sum(1 for geh in geh_values if geh < 5)
            geh_under_5_percent = 100 * geh_under_5_count / n_points

            # Calculate relative gap between total assigned and reference volumes
            total_assigned = sum(assigned)
            total_reference = sum(reference)
            volume_gap = abs(total_assigned - total_reference) / total_reference * 100

            # Create validation result with detailed metrics
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Observed volume comparison: R² = {r_squared:.3f}, RMSE = {rmse:.1f}, MAPE = {mape:.1f}%, {geh_under_5_percent:.1f}% of links with GEH < 5",
                    field="obs_volume",
                    details={
                        "r_squared": float(r_squared),
                        "correlation": float(correlation),
                        "rmse": float(rmse),
                        "mape": float(mape),
                        "geh_under_5_percent": float(geh_under_5_percent),
                        "volume_gap": float(volume_gap),
                        "n_points": n_points,
                        "total_assigned": float(total_assigned),
                        "total_reference": float(total_reference)
                    }
                )
            )

            # Evaluate R² value
            if r_squared < 0.5:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Poor correlation between assigned and observed volumes (R² = {r_squared:.3f})",
                        field="obs_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )
            elif r_squared < 0.75:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Moderate correlation between assigned and observed volumes (R² = {r_squared:.3f})",
                        field="obs_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"Good correlation between assigned and reference volumes (R² = {r_squared:.3f})",
                        field="reference_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )

            # Evaluate MAPE value
            if mape > 25:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"High percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )
            elif mape > 15:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Moderate percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"Low percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )

            # Evaluate volume gap
            if volume_gap > 10:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Large gap between total assigned and reference volumes ({volume_gap:.1f}%)",
                        field="reference_volume",
                        details={"volume_gap": float(volume_gap)}
                    )
                )

            # Identify links with very large differences
            large_diff = volume_comparison[abs(volume_comparison["volume"] - volume_comparison["ref_volume"]) / volume_comparison["ref_volume"] > 1.0]
            if not large_diff.empty:
                large_diff_count = len(large_diff)
                large_diff_percent = 100 * large_diff_count / n_points

                # Sort by difference percentage
                large_diff['diff_pct'] = abs(large_diff["volume"] - large_diff["ref_volume"]) / large_diff["ref_volume"] * 100
                sorted_diff = large_diff.sort_values('diff_pct', ascending=False)

                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {large_diff_count} links ({large_diff_percent:.1f}%) with volume differences >100% from reference",
                        field="reference_volume",
                        details={
                            "large_diff_count": large_diff_count,
                            "large_diff_percent": float(large_diff_percent),
                            "example_links": sorted_diff[["link_id", "volume", "ref_volume", "diff_pct"]].head(5).values.tolist()
                                if all(x in sorted_diff.columns for x in ["link_id", "volume", "ref_volume", "diff_pct"]) else []
                        }
                    )
                )

                # Create CSV output with problem links
                try:
                    output_file = "problem_volume_links.csv"
                    sorted_diff.to_csv(output_file, index=False)
                    print(f"\nLinks with large volume differences written to {output_file}")

                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Exported {large_diff_count} links with large volume differences to {output_file}",
                            field="reference_volume",
                            details={"output_file": output_file}
                        )
                    )
                except Exception as e:
                    print(f"Error writing problem links to CSV: {str(e)}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error comparing assigned and reference volumes: {str(e)}",
                    field="reference_volume"
                )
            )

    def _compare_assigned_reference_volumes(self, link_perf_df):
        """
        Compare assigned volumes with reference volumes.
        Calculate R^2, RMSE, and percentage error metrics.
        """
        try:
            # Filter to links with valid reference volumes
            volume_comparison = link_perf_df[
                (link_perf_df["ref_volume"].notna()) &
                (link_perf_df["ref_volume"] > 0) &
                (link_perf_df["volume"].notna())
            ]

            if len(volume_comparison) == 0:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        "No links with valid reference volumes found for comparison.",
                        field="reference_volume"
                    )
                )
                return

            # Calculate comparison metrics
            n_points = len(volume_comparison)

            # Calculate correlation and R^2
            assigned = volume_comparison["volume"].values
            reference = volume_comparison["ref_volume"].values

            # Calculate means
            assigned_mean = assigned.mean()
            reference_mean = reference.mean()

            # Calculate correlation numerator and denominator
            numerator = sum((assigned[i] - assigned_mean) * (reference[i] - reference_mean) for i in range(n_points))
            denominator = math.sqrt(
                sum((assigned[i] - assigned_mean)**2 for i in range(n_points)) *
                sum((reference[i] - reference_mean)**2 for i in range(n_points))
            )

            correlation = numerator / denominator if denominator != 0 else 0
            r_squared = correlation ** 2

            # Calculate RMSE
            sq_errors = [(assigned[i] - reference[i])**2 for i in range(n_points)]
            rmse = math.sqrt(sum(sq_errors) / n_points)

            # Calculate mean absolute percentage error (MAPE)
            percent_errors = [abs(assigned[i] - reference[i]) / reference[i] for i in range(n_points)]
            mape = 100 * sum(percent_errors) / n_points

            # Calculate GEH statistic for traffic volumes
            geh_values = [
                math.sqrt(2 * (assigned[i] - reference[i])**2 / (assigned[i] + reference[i]))
                if (assigned[i] + reference[i]) > 0 else 0
                for i in range(n_points)
            ]

            geh_under_5_count = sum(1 for geh in geh_values if geh < 5)
            geh_under_5_percent = 100 * geh_under_5_count / n_points

            # Calculate relative gap between total assigned and reference volumes
            total_assigned = sum(assigned)
            total_reference = sum(reference)
            volume_gap = abs(total_assigned - total_reference) / total_reference * 100

            # Create validation result with detailed metrics
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Reference volume comparison: R² = {r_squared:.3f}, RMSE = {rmse:.1f}, MAPE = {mape:.1f}%, {geh_under_5_percent:.1f}% of links with GEH < 5",
                    field="reference_volume",
                    details={
                        "r_squared": float(r_squared),
                        "correlation": float(correlation),
                        "rmse": float(rmse),
                        "mape": float(mape),
                        "geh_under_5_percent": float(geh_under_5_percent),
                        "volume_gap": float(volume_gap),
                        "n_points": n_points,
                        "total_assigned": float(total_assigned),
                        "total_reference": float(total_reference)
                    }
                )
            )

            # Evaluate R² value
            if r_squared < 0.5:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Poor correlation between assigned and reference volumes (R² = {r_squared:.3f})",
                        field="reference_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )
            elif r_squared < 0.75:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Moderate correlation between assigned and reference volumes (R² = {r_squared:.3f})",
                        field="reference_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"Good correlation between assigned and reference volumes (R² = {r_squared:.3f})",
                        field="reference_volume",
                        details={"r_squared": float(r_squared)}
                    )
                )

            # Evaluate MAPE value
            if mape > 25:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"High percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )
            elif mape > 15:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Moderate percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"Low percentage error between assigned and reference volumes (MAPE = {mape:.1f}%)",
                        field="reference_volume",
                        details={"mape": float(mape)}
                    )
                )

            # Evaluate volume gap
            if volume_gap > 10:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Large gap between total assigned and reference volumes ({volume_gap:.1f}%)",
                        field="reference_volume",
                        details={"volume_gap": float(volume_gap)}
                    )
                )

            # Identify links with very large differences
            large_diff = volume_comparison[abs(volume_comparison["volume"] - volume_comparison["ref_volume"]) / volume_comparison["ref_volume"] > 1.0]
            if not large_diff.empty:
                large_diff_count = len(large_diff)
                large_diff_percent = 100 * large_diff_count / n_points

                # Sort by difference percentage
                large_diff['diff_pct'] = abs(large_diff["volume"] - large_diff["ref_volume"]) / large_diff["ref_volume"] * 100
                sorted_diff = large_diff.sort_values('diff_pct', ascending=False)

                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {large_diff_count} links ({large_diff_percent:.1f}%) with volume differences >100% from reference",
                        field="reference_volume",
                        details={
                            "large_diff_count": large_diff_count,
                            "large_diff_percent": float(large_diff_percent),
                            "example_links": sorted_diff[["link_id", "volume", "ref_volume", "diff_pct"]].head(5).values.tolist()
                                if all(x in sorted_diff.columns for x in ["link_id", "volume", "ref_volume", "diff_pct"]) else []
                        }
                    )
                )

                # Create CSV output with problem links
                try:
                    output_file = "problem_volume_links.csv"
                    sorted_diff.to_csv(output_file, index=False)
                    print(f"\nLinks with large volume differences written to {output_file}")

                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Exported {large_diff_count} links with large volume differences to {output_file}",
                            field="reference_volume",
                            details={"output_file": output_file}
                        )
                    )
                except Exception as e:
                    print(f"Error writing problem links to CSV: {str(e)}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error comparing assigned and reference volumes: {str(e)}",
                    field="reference_volume"
                )
            )
    def _check_required_fields(self, df: pd.DataFrame, field_dict: Dict, file_type: str):
        """Check that all required fields are present."""
        required_fields = [field for field, attrs in field_dict.items() 
                          if attrs.get("required", False)]
        
        missing_fields = [field for field in required_fields if field not in df.columns]
        
        if missing_fields:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Missing required fields in {file_type} file: {', '.join(missing_fields)}",
                    details={"missing_fields": missing_fields}
                )
            )
    
    def _check_field_types(self, df: pd.DataFrame, field_dict: Dict, file_type: str):
        """Check that field data types match expected types, properly handling empty/null values."""
        for field, attrs in field_dict.items():
            if field not in df.columns:
                continue
                
            # Count null values for reporting
            null_count = df[field].isna().sum()
            if null_count > 0:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Field '{field}' in {file_type} file contains {null_count} null/empty values",
                        field=field
                    )
                )
                
            # Only validate non-null values
            non_null_df = df.dropna(subset=[field])
            if non_null_df.empty:
                continue
                
            expected_type = attrs.get("type")
            if expected_type == "int":
                # First try to convert to numeric, then check if integers
                numeric_values = pd.to_numeric(non_null_df[field], errors='coerce')
                non_numeric_mask = numeric_values.isna()
                
                if non_numeric_mask.any():
                    # Get the problematic rows
                    problem_rows = non_null_df[non_numeric_mask]
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Field '{field}' in {file_type} file contains {len(problem_rows)} non-integer values",
                            field=field,
                            details={
                                "example_values": problem_rows[field].head(5).tolist(),
                                "example_rows": problem_rows.index.tolist()[:5]
                            }
                        )
                    )
                else:
                    # Now check if all numeric values are integers
                    non_int_mask = ~numeric_values.apply(lambda x: float(x).is_integer())
                    if non_int_mask.any():
                        problem_rows = non_null_df[non_int_mask]
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Field '{field}' in {file_type} file contains {len(problem_rows)} non-integer values (decimal numbers)",
                                field=field,
                                details={
                                    "example_values": problem_rows[field].head(5).tolist(),
                                    "example_rows": problem_rows.index.tolist()[:5]
                                }
                            )
                        )
            
            elif expected_type == "float":
                # Check for values that can't be converted to numeric
                numeric_values = pd.to_numeric(non_null_df[field], errors='coerce')
                non_numeric_mask = numeric_values.isna()
                
                if non_numeric_mask.any():
                    problem_rows = non_null_df[non_numeric_mask]
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Field '{field}' in {file_type} file contains {len(problem_rows)} non-numeric values",
                            field=field,
                            details={
                                "example_values": problem_rows[field].head(5).tolist(),
                                "example_rows": problem_rows.index.tolist()[:5]
                            }
                        )
                    )
            
            elif expected_type == "str":
                # No type validation needed for strings
                pass
    
    def _check_duplicates(self, df: pd.DataFrame, id_field: str, file_type: str):
        """Check for duplicate ID values."""
        if id_field not in df.columns:
            return
            
        duplicates = df[df.duplicated(id_field, keep=False)]
        
        if not duplicates.empty:
            duplicate_ids = duplicates[id_field].unique().tolist()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Duplicate {id_field} values found in {file_type} file",
                    field=id_field,
                    details={"duplicate_ids": duplicate_ids[:10]}
                )
            )
    
    def _check_sorted_nodes(self):
        """Check if nodes are sorted by node_id."""
        if "node_id" not in self.node_df.columns:
            return
            
        if not self.node_df["node_id"].is_monotonic_increasing:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "Nodes are not sorted by node_id in ascending order (Forward-Star Structure)",
                    field="node_id"
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.SUCCESS,
                    "Nodes are correctly sorted by node_id in ascending order",
                    field="node_id"
                )
            )
    
    def _check_sorted_links(self):
        """Check if links are sorted by from_node_id and to_node_id."""
        if "from_node_id" not in self.link_df.columns or "to_node_id" not in self.link_df.columns:
            return
            
        # First check from_node_id sorting
        if not self.link_df["from_node_id"].is_monotonic_increasing:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "Links are not sorted by from_node_id in ascending order (Forward-Star Structure)",
                    field="from_node_id",
                    details={"suggestion": "Use DemandGenerator.sort_and_rewrite_links() to fix this issue"}
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.SUCCESS,
                    "Links are correctly sorted by from_node_id in ascending order",
                    field="from_node_id"
                )
            )
        

            
        # Check to_node_id sorting within from_node_id groups
        from_node_groups = self.link_df.groupby("from_node_id")
        unsorted_groups = []
        
        for name, group in from_node_groups:
            if not group["to_node_id"].is_monotonic_increasing:
                unsorted_groups.append(name)
        
        if unsorted_groups:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "Links are not sorted by to_node_id within from_node_id groups",
                    field="to_node_id",
                    details={"unsorted_from_node_groups": unsorted_groups[:10]}
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.SUCCESS,
                    "Links are correctly sorted by to_node_id within from_node_id groups",
                    field="to_node_id"
                )
            )
    
    def _validate_link_endpoints(self):
        """Check that all link endpoints exist in the node file."""
        if (self.node_df.empty or self.link_df.empty or 
                "node_id" not in self.node_df.columns or
                "from_node_id" not in self.link_df.columns or
                "to_node_id" not in self.link_df.columns):
            return
            
        node_ids = set(self.node_df["node_id"])
        
        # Check from_node_id values
        missing_from_nodes = self.link_df[~self.link_df["from_node_id"].isin(node_ids)]
        if not missing_from_nodes.empty:
            missing_ids = missing_from_nodes["from_node_id"].unique().tolist()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Links reference from_node_id values that don't exist in node file",
                    field="from_node_id",
                    details={"missing_node_ids": missing_ids[:10]}
                )
            )
        
        # Check to_node_id values
        missing_to_nodes = self.link_df[~self.link_df["to_node_id"].isin(node_ids)]
        if not missing_to_nodes.empty:
            missing_ids = missing_to_nodes["to_node_id"].unique().tolist()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Links reference to_node_id values that don't exist in node file",
                    field="to_node_id",
                    details={"missing_node_ids": missing_ids[:10]}
                )
            )
    
    def _check_zone_centroid_structure(self):
        """
        Check node file structure with zone centroids at the beginning.
        - Each zone_id must have a corresponding node with node_id = zone_id
        - All zone centroids must be in a single contiguous block at the beginning
        - Zone IDs must be in non-decreasing order for forward star structure
        - Note: zone_id = 0 is exempt from these checks (typically represents non-zonal nodes)
        """
        if self.node_df is None or "node_id" not in self.node_df.columns or "zone_id" not in self.node_df.columns:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "Cannot check zone centroid structure: required columns missing",
                    field="zone_id"
                )
            )
            return
                
        # Identify zone centroids (where node_id equals zone_id)
        is_centroid = self.node_df["node_id"] == self.node_df["zone_id"]
        centroids = self.node_df[is_centroid]
        non_centroids = self.node_df[~is_centroid]
        
        # Get unique non-null zone_id values (excluding zone_id = 0)
        non_null_zones = set(z for z in self.node_df["zone_id"].unique() 
                             if pd.notna(z) and z != 0)  # Exclude zone_id = 0
        
        # Report zone_id = 0 count for information
        zero_zone_count = len(self.node_df[self.node_df["zone_id"] == 0])
        if zero_zone_count > 0:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Found {zero_zone_count} nodes with zone_id = 0 (exempt from centroid checks)",
                    field="zone_id"
                )
            )
        
        # Check if we have any zone centroids
        if centroids.empty:
            print("\nERROR: No zone centroids found (nodes where node_id == zone_id)")
            print("For each zone_id, there must be exactly one node with node_id equal to zone_id")
            print("These nodes must be placed in a contiguous block at the beginning of the file")
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "No zone centroids found (nodes where node_id == zone_id)",
                    field="zone_id"
                )
            )
            return
        
        # Check for zones without corresponding centroids
        centroid_zones = set(centroids["zone_id"])
        missing_centroids = non_null_zones - centroid_zones
        
        if missing_centroids:
            print(f"\nERROR: Found {len(missing_centroids)} zone_id values without corresponding centroids")
            print(f"Missing centroids for zones: {sorted(list(missing_centroids))[:10]}")
            print("Each zone_id must have exactly one node with node_id = zone_id")
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Found {len(missing_centroids)} zone_id values without corresponding node_id = zone_id",
                    field="zone_id",
                    details={"missing_centroid_zones": sorted(list(missing_centroids))[:10]}
                )
            )
        
        # Check if centroids are in a contiguous block at the beginning
        if not non_centroids.empty:
            # Check if any non-centroid appears before centroids
            if centroids.index.max() >= non_centroids.index.min():
                # Find centroid indices
                centroid_indices = set(centroids.index)
                
                # Check if centroid block is interrupted (not contiguous)
                is_contiguous = (max(centroid_indices) - min(centroid_indices) + 1) == len(centroid_indices)
                
                if not is_contiguous:
                    print("\nERROR: Zone centroids are not in a contiguous block in the node file")
                    print("All zone centroids must be placed together at the beginning of the file")
                    print("This is required for correct forward star structure and efficient shortest path computation")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            "Zone centroids are scattered throughout the node file, not in a contiguous block",
                            field="zone_id"
                        )
                    )
                else:
                    print("\nERROR: Zone centroids are not at the beginning of the node file")
                    print("All zone centroids must be placed at the beginning of the file")
                    print("This is required to correctly identify the first through node")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            "Zone centroids are not listed as the first block in node file",
                            field="zone_id"
                        )
                    )
            else:
                # Check if centroids are in non-decreasing order
                if not centroids["node_id"].is_monotonic_increasing:
                    print("\nWARNING: Zone centroids are not in non-decreasing order by node_id")
                    print("For optimal performance, zone centroids should be ordered by node_id")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            "Zone centroids are not in non-decreasing order by node_id",
                            field="node_id"
                        )
                    )
                else:
                    print("\nSUCCESS: Zone centroids are correctly listed in non-decreasing order at the beginning of the file")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "Zone centroids are correctly listed before physical nodes in non-decreasing order",
                            field="zone_id"
                        )
                    )
        
        # Identify the first through node (first non-centroid node)
        if not non_centroids.empty:
            first_through_node = non_centroids["node_id"].min()
            print(f"\nFirst through node identified as node_id={first_through_node}")
            
            # Store the first through node for use in other validation functions
            self.first_through_node = first_through_node
        else:
            print("\nNo physical nodes found, network contains only zone centroids")
        
        # Report centroid statistics
        print(f"\nFound {len(centroids)} zone centroids out of {len(self.node_df)} total nodes")
        
        self.results.append(
            ValidationResult(
                ValidationStatus.INFO,
                f"Found {len(centroids)} zone centroids out of {len(self.node_df)} total nodes",
                field="zone_id"
            )
        )
        
    def _validate_connectors(self):
        """
        Identify and validate connectors (links between centroids and physical nodes).
        Implements the 'first through node' concept based on the node.csv structure,
        where zone centroids come first, followed by physical nodes.
        """
        if (self.node_df is None or self.link_df.empty or
                "node_id" not in self.node_df.columns or 
                "zone_id" not in self.node_df.columns or
                "from_node_id" not in self.link_df.columns or 
                "to_node_id" not in self.link_df.columns):
            return
            
        # Identify zone centroids (where node_id equals zone_id)
        is_centroid = self.node_df["node_id"] == self.node_df["zone_id"]
        centroids = self.node_df[is_centroid]
        non_centroids = self.node_df[~is_centroid]
        
        if centroids.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "No zone centroids found, can't identify connectors",
                    field="zone_id"
                )
            )
            return
            
        centroid_ids = set(centroids["node_id"])
        
        # Determine the first through node (first physical node after centroids)
        first_through_node = None
        if not non_centroids.empty:
            # Assuming node.csv is sorted with centroids first, followed by physical nodes
            first_through_node = non_centroids["node_id"].min()
            print(f"\nFirst through node identified as node_id={first_through_node}")
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"First through node identified as node_id={first_through_node}",
                    field="node_id"
                )
            )
        else:
            print("\nNo physical nodes found, network contains only zone centroids")
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    "No physical nodes found, network contains only zone centroids",
                    field="node_id"
                )
            )
            
        # Identify connectors (links between centroids and non-centroids)
        connectors = self.link_df[
            ((self.link_df["from_node_id"].isin(centroid_ids)) & (~self.link_df["to_node_id"].isin(centroid_ids))) |
            ((~self.link_df["from_node_id"].isin(centroid_ids)) & (self.link_df["to_node_id"].isin(centroid_ids)))
        ]
        
        # Count connectors
        connector_count = len(connectors)
        self.results.append(
            ValidationResult(
                ValidationStatus.INFO,
                f"Identified {connector_count} connector links between zone centroids and physical nodes",
                field="link_id",
                details={"connector_count": connector_count}
            )
        )
        
        # Check for centroids connecting directly to other centroids
        centroid_to_centroid = self.link_df[
            (self.link_df["from_node_id"].isin(centroid_ids)) & (self.link_df["to_node_id"].isin(centroid_ids))
        ]
        
        if not centroid_to_centroid.empty:
            # In a forward star structure, centroids should only connect to physical nodes (except for special cases)
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,  # Changed to INFO instead of WARNING since direct connections might be valid
                    f"Found {len(centroid_to_centroid)} links directly connecting zone centroids to other zone centroids",
                    field="link_id",
                    details={"centroid_links_count": len(centroid_to_centroid)}
                )
            )
            
                
    def _validate_demand_format(self):
        """
        Validate the demand file has exactly the required three columns in the correct order:
        o_zone_id, d_zone_id, and volume.
        """
        if self.demand_df is None or self.demand_df.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "No demand file provided or file is empty",
                    field="demand"
                )
            )
            return
            
        # Check for required columns
        required_columns = ["o_zone_id", "d_zone_id", "volume"]
        
        # Check if exactly these three columns exist
        if set(self.demand_df.columns) != set(required_columns):
            extra_cols = set(self.demand_df.columns) - set(required_columns)
            missing_cols = set(required_columns) - set(self.demand_df.columns)
            
            message = "Demand file has incorrect column structure."
            details = {}
            
            if missing_cols:
                message += f" Missing columns: {', '.join(missing_cols)}."
                details["missing_columns"] = list(missing_cols)
                
            if extra_cols:
                message += f" Extra columns not allowed: {', '.join(extra_cols)}."
                details["extra_columns"] = list(extra_cols)
                
            message += " Demand file must have exactly 3 columns: o_zone_id, d_zone_id, volume."
            
            print(f"\nERROR: {message}")
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    message,
                    field="demand",
                    details=details
                )
            )
            
        # Check column order
        if list(self.demand_df.columns) != required_columns:
            print("\nERROR: Demand file columns are not in the correct order.")
            print("Required order: o_zone_id, d_zone_id, volume")
            print(f"Current order: {', '.join(self.demand_df.columns)}")
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "Demand file columns are not in the correct order. Required: o_zone_id, d_zone_id, volume",
                    field="demand",
                    details={"current_order": list(self.demand_df.columns)}
                )
            )
                
    def _validate_zone_consistency(self):
        """Check that zones are consistent across node and demand files."""
        if self.node_df is None:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "Cannot validate zone consistency: node file is empty",
                    field="zone_id"
                )
            )
            return
            
        if "zone_id" not in self.node_df.columns:
            print("\nWARNING: 'zone_id' column is not defined in node.csv file!")
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "'zone_id' column is not defined in node.csv file",
                    field="zone_id"
                )
            )
            return
            
        # Get unique zones from node file
        node_zones = set(self.node_df["zone_id"].unique())
        print(f"\nFound {len(node_zones)} unique zone IDs in node file")
        
        # Check if demand file is available
        if self.demand_df is not None and not self.demand_df.empty:
            if "o_zone_id" in self.demand_df.columns and "d_zone_id" in self.demand_df.columns:
                # Get unique zones from demand file
                demand_o_zones = set(self.demand_df["o_zone_id"].unique())
                demand_d_zones = set(self.demand_df["d_zone_id"].unique())
                demand_zones = demand_o_zones.union(demand_d_zones)
                print(f"Found {len(demand_zones)} unique zone IDs in demand file")
                
                # Check for zones in demand but not in node file
                missing_zones = demand_zones - node_zones
                if missing_zones:
                    # Convert to plain integers for readable output
                    missing_zones_list = sorted([int(z) for z in missing_zones])
                    
                    print(f"\nERROR: {len(missing_zones)} zones in demand file are missing from node file!")
                    print(f"Missing zone IDs (first 10): {missing_zones_list[:10]}")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(missing_zones)} zones in demand file that don't exist in node file",
                            field="zone_id",
                            details={"missing_zones": missing_zones_list[:10]}
                        )
                    )
                else:
                    print("\nSUCCESS: All zones in demand file exist in node file")
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "All zones in demand file exist in node file",
                            field="zone_id"
                        )
                    )
            else:
                print("\nWARNING: 'o_zone_id' or 'd_zone_id' columns missing in demand file")
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        "Required zone ID columns missing in demand file",
                        field="zone_id",
                        details={"missing_columns": [col for col in ["o_zone_id", "d_zone_id"] if col not in self.demand_df.columns]}
                    )
                )
        else:
            print("\nWARNING: No demand file available to validate zone consistency")    
        
    def _validate_demand_zones(self):
        """Validate demand file zone IDs."""
        if (self.demand_df is None or self.demand_df.empty or 
                "o_zone_id" not in self.demand_df.columns or 
                "d_zone_id" not in self.demand_df.columns):
            return
            
        # Check for self-loops (origin equals destination)
        self_loops = self.demand_df[self.demand_df["o_zone_id"] == self.demand_df["d_zone_id"]]
        if not self_loops.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Found {len(self_loops)} demand records with same origin and destination zone",
                    field="o_zone_id",
                    details={"self_loop_count": len(self_loops)}
                )
            )
        
        # Check for zero or negative volumes
        if "volume" in self.demand_df.columns:
            invalid_volumes = self.demand_df[self.demand_df["volume"] <= 0]
            if not invalid_volumes.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(invalid_volumes)} demand records with zero or negative volume",
                        field="volume",
                        details={"invalid_volume_count": len(invalid_volumes)}
                    )
                )
    
    def _validate_vdf_parameters(self):
        """Validate volume delay function parameters."""
        vdf_fields = ["vdf_alpha", "vdf_beta", "vdf_fftt", "vdf_length_mi", "vdf_free_speed_mph"]
        
        for field in vdf_fields:
            if field in self.link_df.columns:
                # Check for missing values
                missing = self.link_df[self.link_df[field].isna()]
                if not missing.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(missing)} links with missing {field} values",
                            field=field
                        )
                    )
                
                # Check for negative values
                negative = self.link_df[self.link_df[field] < 0]
                if not negative.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(negative)} links with negative {field} values",
                            field=field
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing required VDF parameter field: {field}",
                        field=field
                    )
                )
    
    def _validate_speed_units(self):
        """Validate that speed values are in expected units (km/h for free_speed, mph for vdf_free_speed_mph)."""
        # Check free_speed (km/h)
        speed_mean=0
        speed_min=0
        speed_max=0
        if "free_speed" in self.link_df.columns:
            # Calculate statistics for speed values
            speed_mean = self.link_df["free_speed"].mean()
            speed_min = self.link_df["free_speed"].min()
            speed_max = self.link_df["free_speed"].max()
            
            # Check if speeds are in reasonable range for km/h
            if speed_mean < 5 or speed_mean > 150:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Average free_speed ({speed_mean:.2f}) is outside typical range for km/h",
                        field="free_speed",
                        details={"mean": speed_mean, "min": speed_min, "max": speed_max}
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Speed values appear to be in km/h (mean: {speed_mean:.2f}, range: {speed_min}-{speed_max})",
                    field="free_speed"
                )
            )
            
        # Check vdf_free_speed_mph (mph)
        if "vdf_free_speed_mph" in self.link_df.columns:
            mph_mean = self.link_df["vdf_free_speed_mph"].mean()
            mph_min = self.link_df["vdf_free_speed_mph"].min()
            mph_max = self.link_df["vdf_free_speed_mph"].max()
            
            # Check if speeds are in reasonable range for mph
            if mph_mean < 3 or mph_mean > 90:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Average vdf_free_speed_mph ({mph_mean:.2f}) is outside typical range for mph",
                        field="vdf_free_speed_mph",
                        details={"mean": mph_mean, "min": mph_min, "max": mph_max}
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"VDF free speed values appear to be in mph (mean: {mph_mean:.2f}, range: {mph_min}-{mph_max})",
                        field="vdf_free_speed_mph"
                    )
                )
                
    def _validate_length_units(self):
             """Validate that length values are in expected units (meters for length, miles for vdf_length_mi)."""
             # Check length (meters)
             if "length" in self.link_df.columns:
                 # Calculate statistics for length values
                 length_mean = self.link_df["length"].mean()
                 length_min = self.link_df["length"].min()
                 length_max = self.link_df["length"].max()
                 
                 # Check for very small values (might be in km instead of meters)
                 if length_mean < 10:
                     self.results.append(
                         ValidationResult(
                             ValidationStatus.WARNING,
                             f"Average link length ({length_mean:.2f}) is very small; may not be in meters",
                             field="length",
                             details={"mean": length_mean, "min": length_min, "max": length_max}
                         )
                     )
                 # Check for very large values
                 elif length_mean > 1000000:
                     self.results.append(
                         ValidationResult(
                             ValidationStatus.WARNING,
                             f"Average link length ({length_mean:.2f}) is very large; may not be in meters",
                             field="length",
                             details={"mean": length_mean, "min": length_min, "max": length_max}
                         )
                     )
                 else:
                    self.results.append(
                         ValidationResult(
                             ValidationStatus.INFO,
                             f"Length values appear to be in meters (mean: {length_mean:.2f}, range: {length_min}-{length_max})",
                             field="length"
                         )
                     )
             
             # Check vdf_length_mi (miles)
             if "vdf_length_mi" in self.link_df.columns:
                 mi_mean = self.link_df["vdf_length_mi"].mean()
                 mi_min = self.link_df["vdf_length_mi"].min()
                 mi_max = self.link_df["vdf_length_mi"].max()
                 
                 # Typical road segment lengths in miles are unlikely to exceed 50 miles
                 if mi_mean > 50:
                     self.results.append(
                         ValidationResult(
                             ValidationStatus.WARNING,
                             f"Average vdf_length_mi ({mi_mean:.2f}) appears too large for miles",
                             field="vdf_length_mi",
                             details={"mean": mi_mean, "min": mi_min, "max": mi_max}
                         )
                     )
                 else:
                     self.results.append(
                         ValidationResult(
                             ValidationStatus.INFO,
                             f"VDF length values appear to be in miles (mean: {mi_mean:.2f}, range: {mi_min}-{mi_max})",
                             field="vdf_length_mi"
                         )
                     )
                 
    def generate_report(self):
        """
        Generate a structured report of validation results.
        
        Returns:
            dict: Dictionary containing organized validation results with summary statistics
        """
        # Organize results by status
        report = {
            "summary": {
                "total": len(self.results),
                "errors": len([r for r in self.results if r.status == ValidationStatus.ERROR]),
                "warnings": len([r for r in self.results if r.status == ValidationStatus.WARNING]),
                "success": len([r for r in self.results if r.status == ValidationStatus.SUCCESS]),
                "info": len([r for r in self.results if r.status == ValidationStatus.INFO])
            },
            "errors": [{"message": r.message, "field": r.field, "details": r.details} 
                      for r in self.results if r.status == ValidationStatus.ERROR],
            "warnings": [{"message": r.message, "field": r.field, "details": r.details} 
                        for r in self.results if r.status == ValidationStatus.WARNING],
            "success": [{"message": r.message, "field": r.field, "details": r.details} 
                       for r in self.results if r.status == ValidationStatus.SUCCESS],
            "info": [{"message": r.message, "field": r.field, "details": r.details} 
                    for r in self.results if r.status == ValidationStatus.INFO],
            "metadata": {
                "node_file": self.node_file,
                "link_file": self.link_file,
                "demand_file": self.demand_file if hasattr(self, 'demand_file') else None,
                "validation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "node_count": len(self.node_df) if not self.node_df is None else 0,
                "link_count": len(self.link_df) if not self.link_df.empty else 0,
                "demand_count": len(self.demand_df) if hasattr(self, 'demand_df') and self.demand_df is not None and not self.demand_df.empty else 0
            }
        }
        
        # Add field-specific statistics
        field_stats = {}
        
        # Node statistics
        if  self.node_df is not None:
            node_stats = {}
            for field in self.node_df.columns:
                try:
                    if self.node_df[field].dtype.kind in 'ifc':  # integer, float, complex
                        node_stats[field] = {
                            "min": float(self.node_df[field].min()),
                            "max": float(self.node_df[field].max()),
                            "mean": float(self.node_df[field].mean()),
                            "null_count": int(self.node_df[field].isna().sum())
                        }
                    else:
                        node_stats[field] = {
                            "unique_values": len(self.node_df[field].unique()),
                            "null_count": int(self.node_df[field].isna().sum())
                        }
                except Exception:
                    # Skip fields that can't be analyzed
                    pass
            field_stats["node"] = node_stats
        
        # Link statistics
        if not self.link_df.empty:
            link_stats = {}
            for field in self.link_df.columns:
                try:
                    if self.link_df[field].dtype.kind in 'ifc':  # integer, float, complex
                        link_stats[field] = {
                            "min": float(self.link_df[field].min()),
                            "max": float(self.link_df[field].max()),
                            "mean": float(self.link_df[field].mean()),
                            "null_count": int(self.link_df[field].isna().sum())
                        }
                    else:
                        link_stats[field] = {
                            "unique_values": len(self.link_df[field].unique()),
                            "null_count": int(self.link_df[field].isna().sum())
                        }
                except Exception:
                    # Skip fields that can't be analyzed
                    pass
            field_stats["link"] = link_stats
        
        # Demand statistics if available
        if hasattr(self, 'demand_df') and self.demand_df is not None and not self.demand_df.empty:
            demand_stats = {}
            for field in self.demand_df.columns:
                try:
                    if self.demand_df[field].dtype.kind in 'ifc':  # integer, float, complex
                        demand_stats[field] = {
                            "min": float(self.demand_df[field].min()),
                            "max": float(self.demand_df[field].max()),
                            "mean": float(self.demand_df[field].mean()),
                            "null_count": int(self.demand_df[field].isna().sum())
                        }
                    else:
                        demand_stats[field] = {
                            "unique_values": len(self.demand_df[field].unique()),
                            "null_count": int(self.demand_df[field].isna().sum())
                        }
                except Exception:
                    # Skip fields that can't be analyzed
                    pass
            field_stats["demand"] = demand_stats
        
        report["field_statistics"] = field_stats
        
        return report

    def print_report(self):
        """Print a formatted validation report to the console."""
        report = self.generate_report()
        
        print("\n===== GMNS Validation Report =====")
        print(f"Total checks: {report['summary']['total']}")
        print(f"Errors: {report['summary']['errors']}")
        print(f"Warnings: {report['summary']['warnings']}")
        print(f"Success: {report['summary']['success']}")
        print(f"Info: {report['summary']['info']}")
        
        if report['errors']:
            print("\n----- ERRORS -----")
            for i, error in enumerate(report['errors'], 1):
                print(f"{i}. {error['message']}" + (f" (Field: {error['field']})" if error['field'] else ""))
        
        if report['warnings']:
            print("\n----- WARNINGS -----")
            for i, warning in enumerate(report['warnings'], 1):
                print(f"{i}. {warning['message']}" + (f" (Field: {warning['field']})" if warning['field'] else ""))
        
        if report['success']:
            print("\n----- SUCCESSES -----")
            for i, success in enumerate(report['success'], 1):
                print(f"{i}. {success['message']}" + (f" (Field: {success['field']})" if success['field'] else ""))
        
        if report['info']:
            print("\n----- INFO -----")
            for i, info in enumerate(report['info'], 1):
                print(f"{i}. {info['message']}" + (f" (Field: {info['field']})" if info['field'] else ""))
        
        # Print metadata
        print("\n----- METADATA -----")
        print(f"Node file: {report['metadata']['node_file']}")
        print(f"Link file: {report['metadata']['link_file']}")
        if report['metadata']['demand_file']:
            print(f"Demand file: {report['metadata']['demand_file']}")
        print(f"Validation time: {report['metadata']['validation_time']}")
        print(f"Node count: {report['metadata']['node_count']}")
        print(f"Link count: {report['metadata']['link_count']}")
        if report['metadata']['demand_count'] > 0:
            print(f"Demand count: {report['metadata']['demand_count']}")
        
        print("\n=======================================")
        
    def _validate_capacity_values(self):
        """
        Validate capacity values for reasonableness and consistency with other fields.
        Checks for:
        - Zero or negative capacity values
        - Unreasonably high capacity values
        - Capacity consistency with link types and number of lanes
        """
        if "link_id" not in self.link_df.columns:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Missing required 'link_id' field in link file",
                    field="link_id"
                )
            )
            return
        if "capacity" not in self.link_df.columns:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Missing required 'capacity' field in link file",
                    field="capacity"
                )
            )
            return
                
        # Calculate statistics for capacity values
        capacity_mean = self.link_df["capacity"].mean()
        capacity_min = self.link_df["capacity"].min()
        capacity_max = self.link_df["capacity"].max()
        
        # Check for zero or negative capacity
        invalid_capacity = self.link_df[self.link_df["capacity"] <= 0]
        if not invalid_capacity.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Found {len(invalid_capacity)} links with zero or negative capacity",
                    field="capacity",
                    details={"invalid_count": len(invalid_capacity), 
                             "example_links": invalid_capacity["link_id"].head(5).tolist()}
                )
            )
        
        # Check for unusually high capacity values
        # Typical highway lane capacity is around 2000-2200 vehicles per hour
        if capacity_max > 3000:
            high_capacity = self.link_df[self.link_df["capacity"] > 5000]
            if len(high_capacity) > 0:  # Only report if there are actually high capacity links
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(high_capacity)} links with unusually high hourly capacity (>3000)",
                        field="capacity",
                        details={"high_capacity_count": len(high_capacity),
                                 "example_links": high_capacity["link_id"].head(5).tolist()}
                    )
                )
        
        # Check capacity consistency with number of lanes if available
        if "lanes" in self.link_df.columns:
            # Calculate capacity per lane
            self.link_df["capacity_per_lane"] = self.link_df["capacity"] / self.link_df["lanes"]
            
            # Check for unreasonably high capacity per lane
            high_cap_per_lane = self.link_df[self.link_df["capacity_per_lane"] > 2500]
            if not high_cap_per_lane.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(high_cap_per_lane)} links with unusually high capacity per lane (>2500)",
                        field="capacity",
                        details={"high_cap_per_lane_count": len(high_cap_per_lane),
                                 "example_links": high_cap_per_lane["link_id"].head(5).tolist()}
                    )
                )
                
            # Check for very low capacity per lane
            low_cap_per_lane = self.link_df[self.link_df["capacity_per_lane"] < 500]
            if not low_cap_per_lane.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(low_cap_per_lane)} links with unusually low capacity per lane (<500)",
                        field="capacity",
                        details={"low_cap_per_lane_count": len(low_cap_per_lane),
                                 "example_links": low_cap_per_lane["link_id"].head(5).tolist()}
                    )
                )
        
        # Check capacity consistency with link types if available
        if "link_type" in self.link_df.columns:
            # Group by link type and calculate statistics
            type_stats = self.link_df.groupby("link_type")["capacity"].agg(["mean", "min", "max", "count"])
            
            # Check for large capacity variations within the same link type
            for link_type, stats in type_stats.iterrows():
                if stats["count"] >= 5:  # Only check link types with enough samples
                    variation = (stats["max"] - stats["min"]) / stats["mean"] if stats["mean"] > 0 else 0
                    
                    if variation > 2.0:  # If max is more than 3x the min (arbitrary threshold)
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Link type {link_type} has large capacity variation (min={stats['min']}, max={stats['max']})",
                                field="capacity",
                                details={"link_type": link_type, 
                                         "capacity_min": stats["min"],
                                         "capacity_max": stats["max"],
                                         "capacity_mean": stats["mean"],
                                         "count": stats["count"]}
                            )
                        )
        
        # Report overall capacity statistics
        self.results.append(
            ValidationResult(
                ValidationStatus.INFO,
                f"Capacity values range from {capacity_min} to {capacity_max} (mean: {capacity_mean:.2f})",
                field="capacity",
                details={"min": capacity_min, "max": capacity_max, "mean": capacity_mean}
            )
        )
        
    def _validate_unit_consistency(self):
        """
        Validate that unit conversions between related fields are consistent.
        Checks:
        - length (meters) vs vdf_length_mi (miles)
        - free_speed (km/h) vs vdf_free_speed_mph (mph)
        - vdf_fftt (minutes) vs calculated values from speed and length
        """
        # Define conversion factors
        MI_TO_M = 1609.34  # miles to meters conversion
        MPH_TO_KMH = 1.60934  # mph to km/h conversion
        
        # Check length (meters) vs vdf_length_mi (miles)
        if "length" in self.link_df.columns and "vdf_length_mi" in self.link_df.columns:
            # Create a temporary dataframe with non-null values in both columns
            df = self.link_df.dropna(subset=["length", "vdf_length_mi"]).copy()
            
            if not df.empty:
                # Calculate expected miles from meters
                df["calc_vdf_length_mi"] = df["length"] / MI_TO_M
                df["length_diff_pct"] = 100 * abs(df["calc_vdf_length_mi"] - df["vdf_length_mi"]) / df["vdf_length_mi"]
                
                # Check for large discrepancies (>5%)
                inconsistent = df[df["length_diff_pct"] > 5]
                if not inconsistent.empty:
                    # Calculate average discrepancy
                    avg_diff = inconsistent["length_diff_pct"].mean()
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {len(inconsistent)} links with inconsistent length/vdf_length_mi conversion (>5% difference, avg={avg_diff:.2f}%)",
                            field="length",
                            details={
                                "inconsistent_count": len(inconsistent),
                                "example_links": inconsistent["link_id"].head(5).tolist(),
                                "example_meters": inconsistent["length"].head(5).tolist(),
                                "example_miles": inconsistent["vdf_length_mi"].head(5).tolist(),
                                "example_diffs": inconsistent["length_diff_pct"].head(5).tolist()
                            }
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "Length (meters) and vdf_length_mi (miles) values are consistent",
                            field="length"
                        )
                    )
        
        # Check free_speed (km/h) vs vdf_free_speed_mph (mph)
        if "free_speed" in self.link_df.columns and "vdf_free_speed_mph" in self.link_df.columns:
            df = self.link_df.dropna(subset=["free_speed", "vdf_free_speed_mph"]).copy()
            
            if not df.empty:
                # Calculate expected mph from km/h
                df["calc_vdf_free_speed_mph"] = df["free_speed"] / MPH_TO_KMH
                df["speed_diff_pct"] = 100 * abs(df["calc_vdf_free_speed_mph"] - df["vdf_free_speed_mph"]) / df["vdf_free_speed_mph"]
                
                # Check for large discrepancies (>5%)
                inconsistent = df[df["speed_diff_pct"] > 5]
                if not inconsistent.empty:
                    avg_diff = inconsistent["speed_diff_pct"].mean()
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {len(inconsistent)} links with inconsistent free_speed/vdf_free_speed_mph conversion (>5% difference, avg={avg_diff:.2f}%)",
                            field="free_speed",
                            details={
                                "inconsistent_count": len(inconsistent),
                                "example_links": inconsistent["link_id"].head(5).tolist(),
                                "example_kmh": inconsistent["free_speed"].head(5).tolist(),
                                "example_mph": inconsistent["vdf_free_speed_mph"].head(5).tolist(),
                                "example_diffs": inconsistent["speed_diff_pct"].head(5).tolist()
                            }
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "Free_speed (km/h) and vdf_free_speed_mph (mph) values are consistent",
                            field="free_speed"
                        )
                    )
        
        # Check vdf_fftt consistency with vdf_length_mi and vdf_free_speed_mph
        if all(field in self.link_df.columns for field in ["vdf_fftt", "vdf_length_mi", "vdf_free_speed_mph"]):
            df = self.link_df.dropna(subset=["vdf_fftt", "vdf_length_mi", "vdf_free_speed_mph"]).copy()
            
            if not df.empty:
                # Calculate expected free flow travel time (minutes) from miles and mph
                # FFTT (min) = length (mi) / speed (mph) * 60
                df["calc_vdf_fftt"] = df["vdf_length_mi"] / df["vdf_free_speed_mph"] * 60
                
                # Add a small epsilon to prevent division by zero
                epsilon = 0.001
                df["fftt_diff_pct"] = 100 * abs(df["calc_vdf_fftt"] - df["vdf_fftt"]) / (df["vdf_fftt"] + epsilon)
                
                # Check for large discrepancies (>5%)
                inconsistent = df[df["fftt_diff_pct"] > 5]
                if not inconsistent.empty:
                    avg_diff = inconsistent["fftt_diff_pct"].mean()
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {len(inconsistent)} links with inconsistent vdf_fftt calculation (>5% difference, avg={avg_diff:.2f}%)",
                            field="vdf_fftt",
                            details={
                                "inconsistent_count": len(inconsistent),
                                "example_links": inconsistent["link_id"].head(5).tolist(),
                                "example_fftt": inconsistent["vdf_fftt"].head(5).tolist(),
                                "example_calc_fftt": inconsistent["calc_vdf_fftt"].head(5).tolist(),
                                "example_diffs": inconsistent["fftt_diff_pct"].head(5).tolist()
                            }
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "VDF free flow travel time (vdf_fftt) values are consistent with length and speed",
                            field="vdf_fftt"
                        )
                    )
        
        # Check consistency between length/free_speed and vdf_fftt (if vdf fields are missing)
        if ("length" in self.link_df.columns and "free_speed" in self.link_df.columns and "vdf_fftt" in self.link_df.columns and
            ("vdf_length_mi" not in self.link_df.columns or "vdf_free_speed_mph" not in self.link_df.columns)):
            
            df = self.link_df.dropna(subset=["length", "free_speed", "vdf_fftt"]).copy()
            
            if not df.empty:
                # Calculate expected free flow travel time (minutes) from meters and km/h
                # FFTT (min) = length (m) / speed (km/h) / 1000 * 60
                df["calc_fftt_min"] = df["length"] / df["free_speed"] / 1000 * 60
                
                # Add a small epsilon to prevent division by zero
                epsilon = 0.001
                df["fftt_diff_pct"] = 100 * abs(df["calc_fftt_min"] - df["vdf_fftt"]) / (df["vdf_fftt"] + epsilon)
                
                # Check for large discrepancies (>10% - using a larger threshold since there might be unit conversions)
                inconsistent = df[df["fftt_diff_pct"] > 10]
                if not inconsistent.empty:
                    avg_diff = inconsistent["fftt_diff_pct"].mean()
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {len(inconsistent)} links with inconsistent vdf_fftt based on length/free_speed (>10% difference, avg={avg_diff:.2f}%)",
                            field="vdf_fftt",
                            details={
                                "inconsistent_count": len(inconsistent),
                                "example_links": inconsistent["link_id"].head(5).tolist(),
                                "example_fftt": inconsistent["vdf_fftt"].head(5).tolist(),
                                "example_calc_fftt": inconsistent["calc_fftt_min"].head(5).tolist(),
                                "example_diffs": inconsistent["fftt_diff_pct"].head(5).tolist()
                            }
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "VDF free flow travel time (vdf_fftt) values are consistent with length and free_speed",
                            field="vdf_fftt"
                        )
                    )
                    
    def _validate_config_files(self):
        """
        Validate configuration files: mode_type.csv and settings.csv.
        Checks for:
        - Presence of required files
        - Required fields in each file
        - Data type validity
        - Consistency with network files
        """
        # Define expected fields for each file
        mode_type_fields = {
            "mode_type": {"type": "str", "required": True, "description": "Mode type identifier"},
            "name": {"type": "str", "required": True, "description": "Mode name"},
            "vot": {"type": "int", "required": True, "description": "Value of time"},
            "pce": {"type": "int", "required": True, "description": "Passenger car equivalent"},
            "occ": {"type": "int", "required": True, "description": "Occupancy"},
            "demand_file": {"type": "str", "required": True, "description": "Demand file for this mode"},
            "dedicated_shortest_path": {"type": "int", "required": True, "description": "Flag for dedicated shortest path"}
        }
        
        settings_fields = {
            "number_of_iterations": {"type": "int", "required": True, "description": "Number of iterations"},
            "number_of_processors": {"type": "int", "required": True, "description": "Number of processors"},
            "demand_period_starting_hours": {"type": "int", "required": True, "description": "Start of demand period in hours"},
            "demand_period_ending_hours": {"type": "int", "required": True, "description": "End of demand period in hours"},
            "base_demand_mode": {"type": "int", "required": True, "description": "Base demand mode"},
            "route_output": {"type": "int", "required": True, "description": "Route output flag"},
            "log_file": {"type": "int", "required": True, "description": "Log file flag"},
            "odme_mode": {"type": "int", "required": True, "description": "OD matrix estimation mode"},
            "odme_vmt": {"type": "int", "required": True, "description": "OD matrix estimation VMT flag"}
        }
        
        # Check mode_type.csv
        mode_type_file = self._find_config_file("mode_type.csv")
        if mode_type_file:
            try:
                mode_type_df = pd.read_csv(mode_type_file)
                # Convert column names to lowercase
                mode_type_df.columns = [col.lower() for col in mode_type_df.columns]
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Found mode_type.csv with {len(mode_type_df)} mode type definitions",
                        field="mode_type"
                    )
                )
                
                # Check required fields
                self._check_required_fields(mode_type_df, mode_type_fields, "mode_type")
                
                # Check data types
                self._check_field_types(mode_type_df, mode_type_fields, "mode_type")
                
                # Count mode types
                mode_count = len(mode_type_df)
                
                # For Level 4 readiness, check if only one mode type is defined
                if mode_count == 1:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "Single mode type defined, satisfying Level 4 readiness criteria",
                            field="mode_type"
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Multiple mode types defined ({mode_count}), which may not satisfy Level 4 readiness criteria",
                            field="mode_type",
                            details={"mode_count": mode_count, 
                                     "modes": mode_type_df["name"].tolist() if "name" in mode_type_df.columns else None}
                        )
                    )
                    
                # Store for future reference
                self.mode_type_df = mode_type_df
                
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Error reading mode_type.csv: {str(e)}",
                        field="mode_type"
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "mode_type.csv file not found",
                    field="mode_type"
                )
            )
        
        # Check settings.csv
        settings_file = self._find_config_file("settings.csv")
        if settings_file:
            try:
                settings_df = pd.read_csv(settings_file)
                # Convert column names to lowercase
                settings_df.columns = [col.lower() for col in settings_df.columns]
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Found settings.csv with {len(settings_df)} configuration rows",
                        field="settings"
                    )
                )
                
                # Check required fields
                self._check_required_fields(settings_df, settings_fields, "settings")
                
                # Check data types
                self._check_field_types(settings_df, settings_fields, "settings")
                
                # Check reasonable values for specific fields
                if "number_of_iterations" in settings_df.columns:
                    iterations = settings_df["number_of_iterations"].iloc[0]
                    if iterations < 10:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Low number of iterations ({iterations}) may lead to poor convergence",
                                field="number_of_iterations in settings.csv"
                            )
                        )
                    elif iterations > 100:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Very high number of iterations ({iterations}) may be inefficient",
                                field="number_of_iterations in settings.csv"
                            )
                        )
                
                # Check demand period hours
                if all(field in settings_df.columns for field in ["demand_period_starting_hours", "demand_period_ending_hours"]):
                    start_hour = settings_df["demand_period_starting_hours"].iloc[0]
                    end_hour = settings_df["demand_period_ending_hours"].iloc[0]
                    
                    # Check if values are non-negative
                    if start_hour < 0 or end_hour < 0:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Demand period hours must be non-negative (start: {start_hour}, end: {end_hour})",
                                field="demand_period_hours in settings.csv"
                            )
                        )
                    
                    # Check if values are within valid range (0-24)
                    if start_hour > 24 or end_hour > 24:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Demand period hours must be ≤ 24 (start: {start_hour}, end: {end_hour})",
                                field="demand_period_hours in settings.csv"
                            )
                        )
                    
                    # Check if end hour is greater than start hour
                    if end_hour <= start_hour:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Demand period ending hour ({end_hour}) must be greater than starting hour ({start_hour})",
                                field="demand_period_hours in settings.csv"
                            )
                        )
                    
                    # Check if demand period is reasonable (≤ 4 hours)
                    period_duration = end_hour - start_hour
                    if period_duration > 4:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.WARNING,
                                f"Demand period duration ({period_duration} hours) exceeds typical maximum of 4 hours",
                                field="demand_period_hours in settings.csv"
                            )
                        )
                
                # Check route output setting for large networks
                if "route_output" in settings_df.columns:
                    route_output = settings_df["route_output"].iloc[0]
                    
                    # Check if route_output is non-negative
                    if route_output < 0:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Route output value ({route_output}) must be non-negative",
                                field="route_output in settings.csv"
                            )
                        )
                    
                    # Check if route_output=1 with a large network
                    if route_output == 1 and hasattr(self, "node_df"):
                        # Count zones (centroids)
                        zone_count = len(self.node_df[self.node_df["node_id"] == self.node_df["zone_id"]])
                        
                        if zone_count > 3000:
                            self.results.append(
                                ValidationResult(
                                    ValidationStatus.WARNING,
                                    f"Route output enabled with a large network ({zone_count} zones). This may be very time-consuming.",
                                    field="route_output",
                                    details={"zone_count": zone_count}
                                )
                            )
                
                # Check if all values are non-negative
                for field in settings_df.columns:
                    if field in settings_fields and settings_fields[field]["type"] in ["int", "float"]:
                        if (settings_df[field] < 0).any():
                            self.results.append(
                                ValidationResult(
                                    ValidationStatus.ERROR,
                                    f"Field '{field}' contains negative values. All settings should be non-negative.",
                                    field=field
                                )
                            )
                
                # Store for future reference
                self.settings_df = settings_df
                
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Error reading settings.csv: {str(e)}",
                        field="settings"
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "settings.csv file not found",
                    field="settings"
                )
            )
        
        # Cross-validation between mode_type and settings
        if hasattr(self, "mode_type_df") and hasattr(self, "settings_df"):
            # Check if base_demand_mode is valid
            if "base_demand_mode" in self.settings_df.columns and "mode_type" in self.mode_type_df.columns:
                base_mode = self.settings_df["base_demand_mode"].iloc[0]
                mode_types = self.mode_type_df["mode_type"].astype(str).tolist()
                
                if str(base_mode) not in mode_types and base_mode != 0:  # 0 might be a special value
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Base demand mode ({base_mode}) in settings.csv does not match any mode_type in mode_type.csv",
                            field="base_demand_mode",
                            details={"base_mode": base_mode, "available_modes": mode_types}
                        )
                    )

    def _find_config_file(self, filename):
        """
        Look for a configuration file in common locations.
        
        Args:
            filename: Name of the file to find
            
        Returns:
            str: Path to the file if found, None otherwise
        """
        filename=os.path.join(self.working_path,filename)
        # Try current directory
        if os.path.exists(filename):
            return filename
        else:
            return None


    """
    ODME (Origin-Destination Matrix Estimation) validation extensions for GMNSValidator.
    This code should be integrated into the GMNSValidator class.
    """
    

    def _validate_observed_volumes(self):
        """Validate observed volumes (obs_volume) in the link file for ODME."""
        if "obs_volume" not in self.link_df.columns:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "Missing 'obs_volume' field in link file. This is required for ODME.",
                    field="obs_volume"
                )
            )
            return
            
        # Check for negative observed volumes
        negative_volumes = self.link_df[self.link_df["obs_volume"] < 0]
        if not negative_volumes.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Found {len(negative_volumes)} links with negative obs_volume values. All values must be non-negative for ODME.",
                    field="obs_volume",
                    details={"negative_count": len(negative_volumes),
                             "example_links": negative_volumes["link_id"].head(5).tolist()}
                )
            )
        
        # Check for links with observed volumes
        links_with_volumes = self.link_df[self.link_df["obs_volume"] > 0]
        if links_with_volumes.empty:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "No links with positive obs_volume values found. ODME requires observed volumes.",
                    field="obs_volume"
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Found {len(links_with_volumes)} links with positive obs_volume values for ODME.",
                    field="obs_volume",
                    details={"volume_links_count": len(links_with_volumes)}
                )
            )
    
    def _validate_odme_configuration(self):
        """Validate ODME-specific settings and files."""
        # Check settings.csv for ODME configuration
        settings_file = self._find_config_file("settings.csv")
        if not settings_file:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    "settings.csv not found. Required for ODME configuration.",
                    field="settings"
                )
            )
            return
            
        try:
            # Load settings
            settings_df = pd.read_csv(settings_file)
            # Convert column names to lowercase
            settings_df.columns = [col.lower() for col in settings_df.columns]
            
            # Check for required ODME fields
            required_odme_fields = ["odme_mode", "odme_vmt", "route_output"]
            missing_fields = [field for field in required_odme_fields if field not in settings_df.columns]
            
            if missing_fields:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing required ODME fields in settings.csv: {', '.join(missing_fields)}",
                        field="settings",
                        details={"missing_fields": missing_fields}
                    )
                )
                return
                
            # Check ODME mode value
            odme_mode = settings_df["odme_mode"].iloc[0]
            if odme_mode == 1:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        "ODME mode is correctly set to 1.",
                        field="odme_mode in settings.csv"
                    )
                )
                
                # Only check route_output if ODME mode is active
                route_output = settings_df["route_output"].iloc[0]
                if route_output != 1:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"route_output is set to {route_output}. Value must be 1 for ODME to generate route_assignment.csv.",
                            field="route_output in settings.csv"
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            "route_output is correctly set to 1 for ODME.",
                            field="route_output"
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"ODME mode is set to {odme_mode}. ODME validation will be skipped.",
                        field="odme_mode"
                    )
                )
                # No need to check route_output or continue with ODME validation
                return
            
            # Check ODME VMT setting
            odme_vmt = settings_df["odme_vmt"].iloc[0]
            if odme_vmt < 0:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"odme_vmt value ({odme_vmt}) must be non-negative.",
                        field="odme_vmt"
                    )
                )
            elif odme_vmt == 0:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        "odme_vmt is set to 0. Target values will not be used in ODME process.",
                        field="odme_vmt"
                    )
                )
            elif odme_vmt >= 2:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"odme_vmt is set to {odme_vmt}. ODME will use target values in the process.",
                        field="odme_vmt"
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"odme_vmt is set to {odme_vmt}.",
                        field="odme_vmt"
                    )
                )
                
            # For ODME validation, we need to check for mode_type.csv and load it
            # Check for and load mode_type.csv if not already loaded
            if not hasattr(self, "mode_type_df"):
                mode_type_file = self._find_config_file("mode_type.csv")
                if not mode_type_file:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            "mode_type.csv not found. Required for ODME to identify demand files.",
                            field="mode_type"
                        )
                    )
                    return
                
                try:
                    # Try to load the mode_type.csv file
                    self.mode_type_df = pd.read_csv(mode_type_file)
                    # Convert column names to lowercase
                    self.mode_type_df.columns = [col.lower() for col in self.mode_type_df.columns]
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            f"Successfully loaded mode_type.csv with {len(self.mode_type_df)} mode definitions.",
                            field="mode_type"
                        )
                    )
                except Exception as e:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Error reading mode_type.csv: {str(e)}",
                            field="mode_type"
                        )
                    )
                    return
            
            # Now that we've ensured mode_type.csv is loaded, validate demand target files
            if hasattr(self, "mode_type_df"):
                self._validate_demand_target_files()
                
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error validating ODME configuration: {str(e)}",
                    field="odme"
                )
            )
        def _validate_demand_target_files(self):
            """
            Validate demand target files required for ODME.
            DTALite adds '_target' suffix to each demand file specified in mode_type.csv.
            """
            if not hasattr(self, "mode_type_df"):
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        "mode_type.csv not loaded. Cannot validate demand target files.",
                        field="demand_target"
                    )
                )
                return
                
            if "demand_file" not in self.mode_type_df.columns:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        "Column 'demand_file' not found in mode_type.csv. Required to identify demand target files.",
                        field="demand_file"
                    )
                )
                return
                
            # Check each demand file has a corresponding target file
            missing_target_files = []
            found_target_files = []
            
            for idx, row in self.mode_type_df.iterrows():
                if pd.isna(row["demand_file"]):
                    continue
                    
                demand_file = str(row["demand_file"]).strip()
                if not demand_file:
                    continue
                    
                # Construct target filename by adding '_target' before the extension
                base, ext = os.path.splitext(demand_file)
                target_file = f"{base}_target{ext}"
                
                # Check if target file exists
                target_path = self._find_config_file(target_file)
                if not target_path:
                    missing_target_files.append(target_file)
                else:
                    found_target_files.append(target_file)
                    
            if missing_target_files:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing demand target files required for ODME: {', '.join(missing_target_files)}",
                        field="demand_target",
                        details={"missing_files": missing_target_files}
                    )
                )
            
            if found_target_files:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        f"Found {len(found_target_files)} demand target files for ODME: {', '.join(found_target_files)}",
                        field="demand_target",
                        details={"found_files": found_target_files}
                    )
                )
            
            if not missing_target_files and not found_target_files:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        "No demand files specified in mode_type.csv. ODME requires at least one demand file with a target.",
                        field="demand_target"
                    )
                )
            
            # Validate content of target files
            for target_file in found_target_files:
                self._validate_demand_target_content(target_file)
        
    def _validate_demand_target_content(self, target_file=None):
        """
        Validate the content of a demand target file to ensure it is properly formatted.
        
        Args:
            target_file: Specific target file to validate. If None, validates all found target files.
        """
        if not hasattr(self, "mode_type_df"):
            return
            
        if "demand_file" not in self.mode_type_df.columns:
            return
        
        # If a specific target file is provided, only validate that one
        target_files_to_check = []
        if target_file:
            target_files_to_check = [target_file]
        else:
            # Otherwise find all target files
            for idx, row in self.mode_type_df.iterrows():
                if pd.isna(row["demand_file"]):
                    continue
                    
                demand_file = str(row["demand_file"]).strip()
                if not demand_file:
                    continue
                    
                # Construct target filename
                base, ext = os.path.splitext(demand_file)
                target_file = f"{base}_target{ext}"
                
                # Check if target file exists
                target_path = self._find_config_file(target_file)
                if target_path:
                    target_files_to_check.append(target_file)
        
        # Validate each target file
        for tgt_file in target_files_to_check:
            target_path = self._find_config_file(tgt_file)
            if not target_path:
                continue
                
            try:
                # Load target file
                target_df = pd.read_csv(target_path)
                
                # Check columns
                required_columns = ["o_zone_id", "d_zone_id", "volume"]
                missing_columns = [col for col in required_columns if col not in target_df.columns]
                
                if missing_columns:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Missing required columns in {tgt_file}: {', '.join(missing_columns)}",
                            field="demand_target_content",
                            details={"file": tgt_file, "missing_columns": missing_columns}
                        )
                    )
                    continue
                    
                # Check data types
                invalid_o_zones = False
                invalid_d_zones = False
                
                # Check o_zone_id is numeric
                if not pd.api.types.is_numeric_dtype(target_df["o_zone_id"]):
                    try:
                        # Try to convert to numeric
                        target_df["o_zone_id"] = pd.to_numeric(target_df["o_zone_id"], errors='coerce')
                        # Check for NaN values after conversion
                        if target_df["o_zone_id"].isna().any():
                            invalid_o_zones = True
                    except:
                        invalid_o_zones = True
                
                # Check d_zone_id is numeric
                if not pd.api.types.is_numeric_dtype(target_df["d_zone_id"]):
                    try:
                        # Try to convert to numeric
                        target_df["d_zone_id"] = pd.to_numeric(target_df["d_zone_id"], errors='coerce')
                        # Check for NaN values after conversion
                        if target_df["d_zone_id"].isna().any():
                            invalid_d_zones = True
                    except:
                        invalid_d_zones = True
                
                if invalid_o_zones:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Invalid o_zone_id values in {tgt_file}. All values must be numeric.",
                            field="demand_target_content",
                            details={"file": tgt_file}
                        )
                    )
                
                if invalid_d_zones:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Invalid d_zone_id values in {tgt_file}. All values must be numeric.",
                            field="demand_target_content",
                            details={"file": tgt_file}
                        )
                    )
                
                # Check for negative volumes
                negative_volumes = target_df[target_df["volume"] < 0]
                if not negative_volumes.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(negative_volumes)} negative volume values in {tgt_file}",
                            field="demand_target_content",
                            details={"file": tgt_file, "negative_count": len(negative_volumes)}
                        )
                    )
                
                # Check for zero volumes (warning only)
                zero_volumes = target_df[target_df["volume"] == 0]
                if not zero_volumes.empty and len(zero_volumes) > len(target_df) / 2:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"More than 50% of volume values in {tgt_file} are zero ({len(zero_volumes)} out of {len(target_df)})",
                            field="demand_target_content",
                            details={"file": tgt_file, "zero_count": len(zero_volumes), "total_records": len(target_df)}
                        )
                    )
                    
                # Check if zones in target file exist in node file
                if "zone_id" in self.node_df.columns:
                    node_zones = set(self.node_df["zone_id"].unique())
                    # Exclude zone_id = 0 from validation as per previous change
                    node_zones = {z for z in node_zones if z != 0}
                    
                    target_o_zones = set(target_df["o_zone_id"].unique())
                    target_d_zones = set(target_df["d_zone_id"].unique())
                    target_zones = target_o_zones | target_d_zones
                    
                    missing_zones = target_zones - node_zones
                    
                    if missing_zones:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Found {len(missing_zones)} zones in {tgt_file} that don't exist in node file",
                                field="demand_target_content",
                                details={"file": tgt_file, "missing_zones": sorted(list(missing_zones))[:10]}
                            )
                        )
                
                # Report success if no issues found
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Validated {tgt_file}: {len(target_df)} OD pairs, total volume: {target_df['volume'].sum():.1f}",
                        field="demand_target_content",
                        details={"file": tgt_file, "records": len(target_df), "total_volume": float(target_df['volume'].sum())}
                    )
                )
                    
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Error validating {tgt_file}: {str(e)}",
                        field="demand_target_content",
                        details={"file": tgt_file}
                    )
                )
    def _validate_demand_target_content(self):
        """Validate the content of demand target files to ensure they are properly formatted."""
        if not hasattr(self, "mode_type_df"):
            return
            
        if "demand_file" not in self.mode_type_df.columns:
            return
            
        for idx, row in self.mode_type_df.iterrows():
            if pd.isna(row["demand_file"]):
                continue
                
            demand_file = str(row["demand_file"]).strip()
            if not demand_file:
                continue
                
            # Construct target filename
            base, ext = os.path.splitext(demand_file)
            target_file = f"{base}_target{ext}"
            
            # Check if target file exists
            target_path = self._find_config_file(target_file)
            if not target_path:
                continue
                
            try:
                # Load target file
                target_df = pd.read_csv(target_path)
                
                # Check columns
                required_columns = ["o_zone_id", "d_zone_id", "volume"]
                missing_columns = [col for col in required_columns if col not in target_df.columns]
                
                if missing_columns:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Missing required columns in {target_file}: {', '.join(missing_columns)}",
                            field="demand_target",
                            details={"file": target_file, "missing_columns": missing_columns}
                        )
                    )
                    continue
                    
                # Check for negative volumes
                negative_volumes = target_df[target_df["volume"] < 0]
                if not negative_volumes.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(negative_volumes)} negative volume values in {target_file}",
                            field="demand_target",
                            details={"file": target_file, "negative_count": len(negative_volumes)}
                        )
                    )
                    
                # Check if zones in target file exist in node file
                if "zone_id" in self.node_df.columns:
                    node_zones = set(self.node_df["zone_id"].unique())
                    target_zones = set(target_df["o_zone_id"].unique()) | set(target_df["d_zone_id"].unique())
                    missing_zones = target_zones - node_zones
                    
                    if missing_zones:
                        self.results.append(
                            ValidationResult(
                                ValidationStatus.ERROR,
                                f"Found {len(missing_zones)} zones in {target_file} that don't exist in node file",
                                field="demand_target",
                                details={"file": target_file, "missing_zones": sorted(list(missing_zones))[:10]}
                            )
                        )
                    
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Error validating {target_file}: {str(e)}",
                        field="demand_target",
                        details={"file": target_file}
                    )
                )


    """
    Enhanced post-simulation validation using standard field names from DTALite output files.
    - Level 6: Accessibility checks
    - Level 7: Traffic assignment validation
    - Level 8: ODME post-quality checks
    """
   
    def _find_output_file(self, filename: str) -> Optional[str]:
        """
        Look for an output file in common locations.
        
        Args:
            filename: Name of the file to find
                
        Returns:
            str: Path to the file if found, None otherwise
        """
        # Try current directory
        filename=os.path.join(self.working_path,filename)
        if os.path.exists(filename):
            return filename
        else:
            return None
    
    def _validate_od_connectivity(self, od_performance_file):
        """
        Validate OD connectivity based on od_performance.csv.
        Checks if all OD pairs in demand files have feasible paths.
        """
        try:
            # Load OD performance data
            od_perf_df = pd.read_csv(od_performance_file)
            
            # Check for required columns based on your file structure
            required_columns = ["o_zone_id", "d_zone_id", "total_distance_km", "total_free_flow_travel_time", 
                               "total_congestion_travel_time", "volume"]
            
            missing_columns = [col for col in required_columns if col not in od_perf_df.columns]
            
            if missing_columns:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing required columns in od_performance.csv: {', '.join(missing_columns)}",
                        field="accessibility",
                        details={"missing_columns": missing_columns}
                    )
                )
                return
                
            # Calculate basic OD connectivity statistics
            total_od_pairs = len(od_perf_df)
            unique_origins = od_perf_df["o_zone_id"].nunique()
            unique_destinations = od_perf_df["d_zone_id"].nunique()
            total_volume = od_perf_df["volume"].sum() if "volume" in od_perf_df.columns else 0
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"OD Performance statistics: {total_od_pairs} OD pairs, {unique_origins} origins, {unique_destinations} destinations, {total_volume:.1f} total volume",
                    field="accessibility",
                    details={
                        "total_od_pairs": total_od_pairs,
                        "unique_origins": unique_origins,
                        "unique_destinations": unique_destinations,
                        "total_volume": float(total_volume)
                    }
                )
            )
            
            # Check for unreasonable travel times
            if "total_congestion_travel_time" in od_perf_df.columns:
                unreasonable_time = od_perf_df[od_perf_df["total_congestion_travel_time"] <= 0]
                if not unreasonable_time.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(unreasonable_time)} OD pairs with zero or negative congestion travel time",
                            field="accessibility",
                            details={"unreasonable_time_count": len(unreasonable_time)}
                        )
                    )
            
            # Check for unreasonable distances
            unreasonable_dist = od_perf_df[od_perf_df["total_distance_km"] <= 0]
            if not unreasonable_dist.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(unreasonable_dist)} OD pairs with zero or negative distance",
                        field="accessibility",
                        details={"unreasonable_dist_count": len(unreasonable_dist)}
                    )
                )
            
            # Check distance ratios if available
            if "distance_ratio" in od_perf_df.columns and "straight_line_distance_km" in od_perf_df.columns:
                # Validate distance metrics
                self._validate_od_distance_metrics(od_perf_df)
                
            # Calculate accessibility metrics for each origin and destination
            self._calculate_accessibility_metrics(od_perf_df)
            
            # FIX: Create a set of OD pairs from od_performance.csv
            # Convert o_zone_id and d_zone_id to integers to ensure consistency
            od_perf_df["o_zone_id"] = od_perf_df["o_zone_id"].astype(int)
            od_perf_df["d_zone_id"] = od_perf_df["d_zone_id"].astype(int)
            
            # Create a set of tuples for fast lookup
            od_perf_pairs = set((int(row["o_zone_id"]), int(row["d_zone_id"])) for _, row in od_perf_df.iterrows())
            
            # Check demand OD connectivity
            self._check_demand_od_connectivity(od_perf_pairs)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error validating OD connectivity: {str(e)}",
                    field="accessibility"
                )
            )
        
    def _calculate_accessibility_metrics(self, od_perf_df):
        """
        Calculate accessibility metrics for each origin and destination.
        - For each origin: number of accessible destinations
        - For each destination: number of origins that can reach it
        """
        try:
            # Group by origin and count destinations
            origin_access = od_perf_df.groupby("o_zone_id").size().reset_index(name="accessible_destinations")
            
            # Group by destination and count origins
            dest_access = od_perf_df.groupby("d_zone_id").size().reset_index(name="reachable_origins")
            
            # Check for origins with poor accessibility
            min_destinations = 5  # Threshold for minimum number of accessible destinations
            poor_access_origins = origin_access[origin_access["accessible_destinations"] < min_destinations]
            
            if not poor_access_origins.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(poor_access_origins)} origins with poor accessibility (< {min_destinations} destinations)",
                        field="accessibility",
                        details={"poor_access_origins": poor_access_origins["o_zone_id"].tolist()[:10]}
                    )
                )
            
            # Check for destinations with poor reachability
            min_origins = 5  # Threshold for minimum number of reachable origins
            poor_reach_dests = dest_access[dest_access["reachable_origins"] < min_origins]
            
            if not poor_reach_dests.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(poor_reach_dests)} destinations with poor reachability (< {min_origins} origins)",
                        field="accessibility",
                        details={"poor_reach_dests": poor_reach_dests["d_zone_id"].tolist()[:10]}
                    )
                )
            
            # Calculate overall network accessibility metrics
            avg_accessible_destinations = origin_access["accessible_destinations"].mean()
            avg_reachable_origins = dest_access["reachable_origins"].mean()
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Accessibility metrics: Avg destinations per origin = {avg_accessible_destinations:.1f}, Avg origins per destination = {avg_reachable_origins:.1f}",
                    field="accessibility",
                    details={
                        "avg_accessible_destinations": float(avg_accessible_destinations),
                        "avg_reachable_origins": float(avg_reachable_origins)
                    }
                )
            )
            
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error calculating accessibility metrics: {str(e)}",
                    field="accessibility"
                )
            )
    
    def _check_demand_od_connectivity(self, od_perf_pairs):
        """
        Check if all significant OD pairs from demand files have corresponding entries in od_performance.
        OD pairs with significant volume (>10) should have feasible paths.
        Includes detailed reporting of disconnected OD pairs.
        
        Args:
            od_perf_pairs: Set of (o_zone_id, d_zone_id) tuples from od_performance.csv
        """
        if not hasattr(self, "mode_type_df"):
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "mode_type.csv not loaded. Cannot check demand-performance connectivity.",
                    field="accessibility"
                )
            )
            return
            
        if "demand_file" not in self.mode_type_df.columns:
            self.results.append(
                ValidationResult(
                    ValidationStatus.WARNING,
                    "mode_type.csv does not contain demand_file column. Cannot check demand-performance connectivity.",
                    field="accessibility"
                )
            )
            return
        
        # Count total and disconnected OD pairs across all demand files
        total_od_count = 0
        significant_od_count = 0
        disconnected_od_count = 0
        disconnected_volume = 0
        total_volume = 0
        
        # Track disconnected OD pairs for detailed reporting
        all_disconnected_pairs = []
        
        # Process each demand file
        for idx, row in self.mode_type_df.iterrows():
            if pd.isna(row["demand_file"]):
                continue
                
            demand_file = str(row["demand_file"]).strip()
            if not demand_file:
                continue
                
            demand_path = self._find_config_file(demand_file)
            if not demand_path:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Demand file {demand_file} specified in mode_type.csv not found",
                        field="accessibility",
                        details={"missing_file": demand_file}
                    )
                )
                continue
                
            try:
                # Load demand file
                demand_df = pd.read_csv(demand_path)
                
                # Check for required columns
                if not all(col in demand_df.columns for col in ["o_zone_id", "d_zone_id", "volume"]):
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Demand file {demand_file} is missing required columns",
                            field="accessibility",
                            details={"file": demand_file}
                        )
                    )
                    continue
                
                # Ensure zone IDs are integers for consistent comparison
                demand_df["o_zone_id"] = demand_df["o_zone_id"].astype(int)
                demand_df["d_zone_id"] = demand_df["d_zone_id"].astype(int)
                    
                # Count total ODs and volume
                file_total_od = len(demand_df)
                file_total_volume = demand_df["volume"].sum()
                
                # Identify significant OD pairs (volume > 10)
                significant_ods = demand_df[demand_df["volume"] > 10]
                file_significant_od = len(significant_ods)
                
                # Check which significant OD pairs are not in the performance file
                file_disconnected_count = 0
                file_disconnected_volume = 0
                file_disconnected_pairs = []
                
                for _, od_row in significant_ods.iterrows():
                    # Create tuple with integers for consistent comparison
                    od_pair = (int(od_row["o_zone_id"]), int(od_row["d_zone_id"]))
                    
                    if od_pair not in od_perf_pairs:
                        file_disconnected_count += 1
                        file_disconnected_volume += od_row["volume"]
                        
                        # Store disconnected pair details
                        file_disconnected_pairs.append({
                            "o_zone_id": int(od_row["o_zone_id"]),
                            "d_zone_id": int(od_row["d_zone_id"]),
                            "volume": float(od_row["volume"]),
                            "demand_file": demand_file
                        })
                
                # Update totals
                total_od_count += file_total_od
                significant_od_count += file_significant_od
                disconnected_od_count += file_disconnected_count
                disconnected_volume += file_disconnected_volume
                total_volume += file_total_volume
                all_disconnected_pairs.extend(file_disconnected_pairs)
                
                # Report file-specific results
                if file_disconnected_count > 0:
                    # Sort disconnected pairs by volume (largest first)
                    sorted_pairs = sorted(file_disconnected_pairs, key=lambda x: x["volume"], reverse=True)
                    
                    # Take top 10 pairs for reporting
                    top_pairs = sorted_pairs[:10]
                    
                    # Format for display: "O=123, D=456, Volume=789.0"
                    formatted_pairs = [
                        f"O={p['o_zone_id']}, D={p['d_zone_id']}, Volume={p['volume']:.1f}" 
                        for p in top_pairs
                    ]
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Demand file {demand_file}: {file_disconnected_count} significant OD pairs ({file_disconnected_volume:.1f} trips) have no feasible path",
                            field="accessibility",
                            details={
                                "file": demand_file,
                                "disconnected_count": file_disconnected_count,
                                "disconnected_volume": float(file_disconnected_volume),
                                "disconnected_percentage": float(file_disconnected_count / max(1, file_significant_od) * 100),
                                "disconnected_pairs": formatted_pairs
                            }
                        )
                    )
                    
                    # Print the disconnected pairs to the console for immediate visibility
                    print(f"\nDisconnected OD pairs in {demand_file} (top {len(top_pairs)} of {file_disconnected_count}):")
                    for pair in formatted_pairs:
                        print(f"  {pair}")
                        
                else:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.SUCCESS,
                            f"Demand file {demand_file}: All significant OD pairs have feasible paths",
                            field="accessibility",
                            details={"file": demand_file}
                        )
                    )
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Error checking connectivity for demand file {demand_file}: {str(e)}",
                        field="accessibility",
                        details={"file": demand_file, "error": str(e)}
                    )
                )
        
        # Report overall results
        if total_od_count > 0:
            disconnected_percent = disconnected_od_count / max(1, significant_od_count) * 100
            disconnected_volume_percent = disconnected_volume / max(1.0, total_volume) * 100
            
            if disconnected_od_count > 0:
                # Sort all disconnected pairs by volume
                sorted_all_pairs = sorted(all_disconnected_pairs, key=lambda x: x["volume"], reverse=True)
                
                # Take top 20 overall pairs
                top_overall_pairs = sorted_all_pairs[:20]
                
                # Format for display with demand file information
                formatted_overall = [
                    f"O={p['o_zone_id']}, D={p['d_zone_id']}, Volume={p['volume']:.1f}, File={p['demand_file']}" 
                    for p in top_overall_pairs
                ]
                
                # Determine status based on percentage
                if disconnected_percent > 5:  # More than 5% of significant OD pairs are disconnected
                    status = ValidationStatus.ERROR
                else:
                    status = ValidationStatus.WARNING
                    
                self.results.append(
                    ValidationResult(
                        status,
                        f"Overall network connectivity: {disconnected_od_count} significant OD pairs ({disconnected_percent:.1f}%) with {disconnected_volume:.1f} trips ({disconnected_volume_percent:.1f}%) have no feasible path",
                        field="accessibility",
                        details={
                            "disconnected_count": disconnected_od_count,
                            "disconnected_percentage": float(disconnected_percent),
                            "disconnected_volume": float(disconnected_volume),
                            "disconnected_volume_percentage": float(disconnected_volume_percent),
                            "top_disconnected_pairs": formatted_overall
                        }
                    )
                )
                
                # Print overall top disconnected pairs
                print(f"\nOverall top disconnected OD pairs (top {len(top_overall_pairs)} of {disconnected_od_count}):")
                for pair in formatted_overall:
                    print(f"  {pair}")
                    
                # Create a CSV output file with all disconnected pairs
                try:
                    import csv
                    output_file = "disconnected_od_pairs.csv"
                    
                    with open(output_file, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(["o_zone_id", "d_zone_id", "volume", "demand_file"])
                        
                        for pair in all_disconnected_pairs:
                            writer.writerow([
                                pair["o_zone_id"], 
                                pair["d_zone_id"], 
                                pair["volume"],
                                pair["demand_file"]
                            ])
                            
                    print(f"\nComplete list of disconnected OD pairs written to {output_file}")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Complete list of {disconnected_od_count} disconnected OD pairs written to {output_file}",
                            field="accessibility",
                            details={"output_file": output_file}
                        )
                    )
                    
                except Exception as e:
                    print(f"Error writing disconnected OD pairs to CSV: {str(e)}")
                    
            else:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.SUCCESS,
                        "Overall network connectivity: All significant OD pairs have feasible paths",
                        field="accessibility"
                    )
                )
    def _validate_od_distance_metrics(self, od_perf_df):
        """
        Validate the distance metrics in OD performance data to check for unreasonable values.
        
        Checks:
        1. Consistency between kilometers and miles
        2. Reasonable distance ratios
        3. Reasonable absolute distances
        4. Identifies potentially erroneous OD pairs
        """
        try:
            # Check required columns
            required_columns = ["o_zone_id", "d_zone_id", "total_distance_km", 
                              "straight_line_distance_mile", "straight_line_distance_km", "distance_ratio"]
            
            missing_columns = [col for col in required_columns if col not in od_perf_df.columns]
            if missing_columns:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Missing distance columns in od_performance.csv: {', '.join(missing_columns)}. Cannot validate distance metrics.",
                        field="accessibility_distance",
                        details={"missing_columns": missing_columns}
                    )
                )
                return
                
            # Create a clean dataframe for analysis
            distance_df = od_perf_df[required_columns].copy()
            
            # Filter out rows with missing values
            valid_rows = distance_df.dropna(subset=required_columns)
            if len(valid_rows) < len(distance_df):
                missing_count = len(distance_df) - len(valid_rows)
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {missing_count} OD pairs with missing distance values",
                        field="accessibility_distance",
                        details={"missing_count": missing_count}
                    )
                )
                
            # 1. Check consistency between kilometers and miles
            # Theoretical conversion factor: 1 mile = 1.60934 km
            valid_rows['mile_km_ratio'] = valid_rows['straight_line_distance_km'] / valid_rows['straight_line_distance_mile']
            inconsistent_conversion = valid_rows[
                (valid_rows['mile_km_ratio'] < 1.5) | (valid_rows['mile_km_ratio'] > 1.7)
            ]
            
            if not inconsistent_conversion.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(inconsistent_conversion)} OD pairs with inconsistent mile/km conversion",
                        field="accessibility_distance",
                        details={
                            "inconsistent_count": len(inconsistent_conversion),
                            "example_pairs": inconsistent_conversion[["o_zone_id", "d_zone_id", "straight_line_distance_mile", 
                                                                     "straight_line_distance_km", "mile_km_ratio"]].head(10).values.tolist()
                        }
                    )
                )
                
            # 2. Check for unreasonable distance ratios
            # distance_ratio = network_distance / straight_line_distance
            
            # Very low ratios (route much shorter than straight line) - physically impossible
            very_low_ratio = valid_rows[valid_rows['distance_ratio'] < 0.8]
            if not very_low_ratio.empty:
                # Sort by most problematic (lowest ratio) first
                very_low_ratio = very_low_ratio.sort_values('distance_ratio')
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(very_low_ratio)} OD pairs with impossibly low distance ratios (<0.8) - network distance shorter than straight line",
                        field="accessibility_distance",
                        details={
                            "very_low_count": len(very_low_ratio),
                            "example_pairs": very_low_ratio[["o_zone_id", "d_zone_id", "total_distance_km", 
                                                           "straight_line_distance_km", "distance_ratio"]].head(10).values.tolist()
                        }
                    )
                )
                
                # Print to console for immediate visibility
                print("\nOD pairs with impossibly low distance ratios (network distance shorter than straight line):")
                for i, row in very_low_ratio.head(10).iterrows():
                    print(f"  O={int(row['o_zone_id'])}, D={int(row['d_zone_id'])}, Network={row['total_distance_km']:.2f}km, "
                          f"Straight={row['straight_line_distance_km']:.2f}km, Ratio={row['distance_ratio']:.6f}")
            
            # Very high ratios (extremely circuitous routes)
            very_high_ratio = valid_rows[valid_rows['distance_ratio'] > 5.0]
            if not very_high_ratio.empty:
                # Sort by most problematic (highest ratio) first
                very_high_ratio = very_high_ratio.sort_values('distance_ratio', ascending=False)
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(very_high_ratio)} OD pairs with very high distance ratios (>5.0) - extremely circuitous routes",
                        field="accessibility_distance",
                        details={
                            "very_high_count": len(very_high_ratio),
                            "example_pairs": very_high_ratio[["o_zone_id", "d_zone_id", "total_distance_km", 
                                                            "straight_line_distance_km", "distance_ratio"]].head(10).values.tolist()
                        }
                    )
                )
                
                # Print to console for immediate visibility
                print("\nOD pairs with extremely high distance ratios (very circuitous routes):")
                for i, row in very_high_ratio.head(10).iterrows():
                    print(f"  O={int(row['o_zone_id'])}, D={int(row['d_zone_id'])}, Network={row['total_distance_km']:.2f}km, "
                          f"Straight={row['straight_line_distance_km']:.2f}km, Ratio={row['distance_ratio']:.6f}")
            
            # 3. Check for unreasonable absolute distances
            # Identify OD pairs with very large network distances
            very_large_distance = valid_rows[valid_rows['total_distance_km'] > 500]
            if not very_large_distance.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.WARNING,
                        f"Found {len(very_large_distance)} OD pairs with very large network distances (>500 km)",
                        field="accessibility_distance",
                        details={
                            "large_distance_count": len(very_large_distance),
                            "example_pairs": very_large_distance[["o_zone_id", "d_zone_id", "total_distance_km"]].head(10).values.tolist()
                        }
                    )
                )
            
            # 4. Check for mismatch between ratios and actual values
            # Identify cases where the stored ratio doesn't match calculated ratio
            valid_rows['calculated_ratio'] = valid_rows['total_distance_km'] / valid_rows['straight_line_distance_km']
            ratio_discrepancy = valid_rows[abs(valid_rows['calculated_ratio'] - valid_rows['distance_ratio']) > 0.01]
            
            if not ratio_discrepancy.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(ratio_discrepancy)} OD pairs where stored distance_ratio doesn't match calculated value",
                        field="accessibility_distance",
                        details={
                            "discrepancy_count": len(ratio_discrepancy),
                            "example_pairs": ratio_discrepancy[["o_zone_id", "d_zone_id", "distance_ratio", "calculated_ratio"]].head(10).values.tolist()
                        }
                    )
                )
            
            # Generate overall statistics
            avg_ratio = valid_rows['distance_ratio'].mean()
            min_ratio = valid_rows['distance_ratio'].min()
            max_ratio = valid_rows['distance_ratio'].max()
            median_ratio = valid_rows['distance_ratio'].median()
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Distance ratio statistics: Min={min_ratio:.4f}, Max={max_ratio:.4f}, Avg={avg_ratio:.4f}, Median={median_ratio:.4f}",
                    field="accessibility_distance",
                    details={
                        "min_ratio": float(min_ratio),
                        "max_ratio": float(max_ratio),
                        "avg_ratio": float(avg_ratio),
                        "median_ratio": float(median_ratio)
                    }
                )
            )
            
            # Export problematic OD pairs to CSV for detailed analysis
            problematic_pairs = pd.concat([very_low_ratio, very_high_ratio]).drop_duplicates()
            if not problematic_pairs.empty:
                try:
                    output_file = os.path.join(self.working_path,"problematic_od_distances.csv")
                    problematic_pairs.to_csv(output_file, index=False)
                    print(f"\nProblematic OD distance metrics written to {output_file}")
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.INFO,
                            f"Exported {len(problematic_pairs)} OD pairs with problematic distance metrics to {output_file}",
                            field="accessibility_distance",
                            details={"output_file": output_file}
                        )
                    )
                except Exception as e:
                    print(f"Error writing problematic OD distances to CSV: {str(e)}")
            
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error validating OD distance metrics: {str(e)}",
                    field="accessibility_distance"
                )
            )
        
    def _validate_route_assignments(self, route_assignment_file):
        """
        Validate route assignments from route_assignment.csv.
        - Check route characteristics
        - Validate multiple routes per OD pair
        - Identify OD pairs with unreasonable routes
        """
        try:
            # Load route assignment data
            route_df = pd.read_csv(route_assignment_file)
            
            # Check for required columns based on your file structure
            required_columns = ["o_zone_id", "d_zone_id", "distance_mile", "total_distance_km", "total_free_flow_travel_time", 
                               "total_travel_time", "volume", "prob"]
            
            missing_columns = [col for col in required_columns if col not in route_df.columns]
            
            if missing_columns:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Missing required columns in route_assignment.csv: {', '.join(missing_columns)}",
                        field="route_assignment",
                        details={"missing_columns": missing_columns}
                    )
                )
                return
                
            # Calculate basic route statistics
            total_routes = len(route_df)
            unique_od_pairs = route_df[["o_zone_id", "d_zone_id"]].drop_duplicates().shape[0]
            avg_routes_per_od = total_routes / unique_od_pairs if unique_od_pairs > 0 else 0
            
            self.results.append(
                ValidationResult(
                    ValidationStatus.INFO,
                    f"Route assignment statistics: {total_routes} routes for {unique_od_pairs} OD pairs (avg {avg_routes_per_od:.2f} routes per OD)",
                    field="route_assignment",
                    details={
                        "total_routes": total_routes,
                        "unique_od_pairs": unique_od_pairs,
                        "avg_routes_per_od": float(avg_routes_per_od)
                    }
                )
            )
            
            # Check for OD pairs with multiple routes
            od_route_counts = route_df.groupby(["o_zone_id", "d_zone_id"]).size().reset_index(name="route_count")
            multiple_route_ods = od_route_counts[od_route_counts["route_count"] > 1]
            
            if not multiple_route_ods.empty:
                multiple_route_count = len(multiple_route_ods)
                multiple_route_percent = 100 * multiple_route_count / unique_od_pairs
                
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Found {multiple_route_count} OD pairs ({multiple_route_percent:.1f}%) with multiple route choices",
                        field="route_assignment",
                        details={
                            "multiple_route_count": multiple_route_count,
                            "multiple_route_percent": float(multiple_route_percent)
                        }
                    )
                )
            
            # Check route probabilities sum to 1 for each OD pair
            od_prob_sums = route_df.groupby(["o_zone_id", "d_zone_id"])["prob"].sum().reset_index(name="prob_sum")
            invalid_probs = od_prob_sums[(od_prob_sums["prob_sum"] < 0.99) | (od_prob_sums["prob_sum"] > 1.01)]
            
            if not invalid_probs.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(invalid_probs)} OD pairs where route probabilities don't sum to 1.0",
                        field="route_assignment",
                        details={
                            "invalid_prob_count": len(invalid_probs),
                            "example_ods": invalid_probs.head(5)[["o_zone_id", "d_zone_id", "prob_sum"]].values.tolist()
                        }
                    )
                )
            
            # Check for unreasonable travel times
            unreasonable_time = route_df[route_df["total_travel_time"] <= 0]
            if not unreasonable_time.empty:
                self.results.append(
                    ValidationResult(
                        ValidationStatus.ERROR,
                        f"Found {len(unreasonable_time)} routes with zero or negative travel time",
                        field="route_assignment",
                        details={"unreasonable_time_count": len(unreasonable_time)}
                    )
                )
            
            # Check free flow vs congested travel times
            if "total_free_flow_travel_time" in route_df.columns and "total_travel_time" in route_df.columns:
                # Calculate congestion ratio
                route_df["congestion_ratio"] = route_df["total_travel_time"] / route_df["total_free_flow_travel_time"]
                
                # Check for unreasonable congestion ratios
                high_congestion = route_df[route_df["congestion_ratio"] > 5]
                if not high_congestion.empty:
                    high_congestion_count = len(high_congestion)
                    high_congestion_percent = 100 * high_congestion_count / len(route_df)
                    
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.WARNING,
                            f"Found {high_congestion_count} routes ({high_congestion_percent:.1f}%) with extremely high congestion (>5x free flow time)",
                            field="route_assignment",
                            details={
                                "high_congestion_count": high_congestion_count,
                                "high_congestion_percent": float(high_congestion_percent),
                                "example_routes": high_congestion[["o_zone_id", "d_zone_id", "congestion_ratio"]].head(5).values.tolist()
                            }
                        )
                    )
                
                # Check for travel times faster than free flow
                invalid_congestion = route_df[route_df["congestion_ratio"] < 0.99]
                if not invalid_congestion.empty:
                    self.results.append(
                        ValidationResult(
                            ValidationStatus.ERROR,
                            f"Found {len(invalid_congestion)} routes with travel times faster than free flow",
                            field="route_assignment",
                            details={
                                "invalid_congestion_count": len(invalid_congestion),
                                "example_routes": invalid_congestion[["o_zone_id", "d_zone_id", "congestion_ratio"]].head(5).values.tolist()
                            }
                        )
                    )
                
                # Calculate average congestion ratio
                avg_congestion = route_df["congestion_ratio"].mean()
                self.results.append(
                    ValidationResult(
                        ValidationStatus.INFO,
                        f"Average congestion ratio (travel time / free flow time): {avg_congestion:.2f}",
                        field="route_assignment",
                        details={"avg_congestion": float(avg_congestion)}
                    )
                )
            
        except Exception as e:
            self.results.append(
                ValidationResult(
                    ValidationStatus.ERROR,
                    f"Error validating route assignments: {str(e)}",
                    field="route_assignment"
                )
            )
    
