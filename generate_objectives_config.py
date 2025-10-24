#!/usr/bin/env python3
"""
Generate Objectives Config Script

This script runs before the main application to generate objectives_config.json
from the objective definition files. It scans all definition files and extracts
required and optional parameters to create validation config for the parser.

Usage:
    python generate_objectives_config.py
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Set, List


def scan_definition_file(definition_path: Path) -> Dict[str, Any]:
    """
    Scan a single objective definition file and extract parameter requirements.
    
    Args:
        definition_path: Path to the definition JSON file
        
    Returns:
        Dictionary with objective info including required and optional fields
    """
    print(f"[SCANNER] Processing: {definition_path.name}")
    
    try:
        with open(definition_path, 'r') as f:
            definition_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read {definition_path}: {e}")
        return {}
    
    # Extract definitions
    definitions = definition_data.get("definitions", {})
    
    result = {}
    
    # Process each objective type in the file
    for objective_type, actions in definitions.items():
        print(f"[SCANNER]   - Found objective type: {objective_type}")
        
        required_fields: Dict[str, Dict[str, str]] = {}
        optional_fields: Dict[str, Dict[str, Any]] = {}
        seen_params: Set[str] = set()
        
        # Scan all actions to collect parameters
        for action in actions:
            action_type = action.get("action_type", "unknown")
            parameters = action.get("parameters", {})
            
            for param_name, param_value in parameters.items():
                # Skip if we've already processed this parameter
                if param_name in seen_params:
                    continue
                
                seen_params.add(param_name)
                
                # Determine if required (empty string) or optional (has default value)
                if param_value == "":
                    # Required field - empty string means it must be provided
                    required_fields[param_name] = {
                        "type": _infer_type(param_name),
                        "description": _generate_description(param_name)
                    }
                    
                    # Add format hint for date fields
                    if "date" in param_name.lower():
                        required_fields[param_name]["format"] = "MM/DD/YYYY"
                        
                else:
                    # Optional field - has a default value
                    optional_fields[param_name] = {
                        "type": _infer_type(param_name, param_value),
                        "description": _generate_description(param_name),
                        "default": param_value
                    }
        
        # Build objective config
        objective_config = {
            "description": _generate_objective_description(objective_type),
            "required_fields": required_fields,
            "optional_fields": optional_fields
        }
        
        result[objective_type] = objective_config
        
        print(f"[SCANNER]     • Required fields: {len(required_fields)}")
        print(f"[SCANNER]     • Optional fields: {len(optional_fields)}")
    
    return result


def _infer_type(param_name: str, param_value: Any = None) -> str:
    """
    Infer the type of a parameter from its name and value.
    
    Args:
        param_name: Name of the parameter
        param_value: Optional value to help determine type
        
    Returns:
        Type as string ("string", "number", "boolean")
    """
    param_lower = param_name.lower()
    
    # Check value type if provided
    if param_value is not None:
        if isinstance(param_value, bool):
            return "boolean"
        elif isinstance(param_value, (int, float)):
            return "number"
        elif isinstance(param_value, str):
            return "string"
    
    # Infer from name patterns
    if any(keyword in param_lower for keyword in ["percent", "timeout", "count", "number"]):
        return "number"
    elif any(keyword in param_lower for keyword in ["is_", "has_", "should_", "enabled", "disabled"]):
        return "boolean"
    else:
        return "string"


def _generate_description(param_name: str) -> str:
    """
    Generate a human-readable description from a parameter name.
    
    Args:
        param_name: Name of the parameter (e.g., "advertiser_name")
        
    Returns:
        Human-readable description
    """
    # Convert snake_case to Title Case
    words = param_name.replace("_", " ").title()
    
    # Add context
    if "date" in param_name.lower():
        return f"{words} for the instruction"
    elif "name" in param_name.lower():
        return f"Name of the {param_name.replace('_name', '').replace('_', ' ')}"
    elif "number" in param_name.lower():
        return f"{words}"
    elif "isci" in param_name.lower():
        return f"{words} code"
    elif "percent" in param_name.lower():
        return f"{words}"
    elif "timeout" in param_name.lower():
        return f"Timeout in seconds for {param_name.replace('_timeout', '').replace('timeout', 'operation')}"
    else:
        return words


def _generate_objective_description(objective_type: str) -> str:
    """
    Generate a description for an objective type.
    
    Args:
        objective_type: Name of the objective type
        
    Returns:
        Human-readable description
    """
    # Convert to title case and add context
    words = objective_type.replace("_", " ").title()
    return f"{words} - Automated workflow objective"


def generate_config(definitions_dir: str = "src/workflow_module/objective_definitions",
                   output_file: str = "objectives_config.json") -> bool:
    """
    Generate objectives_config.json from all definition files.
    
    Args:
        definitions_dir: Directory containing objective definition files
        output_file: Output path for the generated config file
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*70)
    print("GENERATING OBJECTIVES CONFIG")
    print("="*70)
    
    definitions_path = Path(definitions_dir)
    
    if not definitions_path.exists():
        print(f"[ERROR] Definitions directory not found: {definitions_dir}")
        return False
    
    print(f"[INFO] Scanning directory: {definitions_dir}")
    
    # Collect all objective configs
    all_objectives = {}
    
    # Find all JSON files
    json_files = list(definitions_path.glob("*.json"))
    
    if not json_files:
        print(f"[WARNING] No JSON files found in {definitions_dir}")
        return False
    
    print(f"[INFO] Found {len(json_files)} definition file(s)")
    
    # Process each definition file
    for json_file in json_files:
        objectives = scan_definition_file(json_file)
        all_objectives.update(objectives)
    
    # Build final config structure
    config = {
        "objectives": all_objectives
    }
    
    # Write to output file
    print(f"\n[INFO] Writing config to: {output_file}")
    try:
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"[SUCCESS] Config file generated successfully!")
        print(f"[SUCCESS] Total objectives: {len(all_objectives)}")
        
        # Print summary
        print(f"\n{'-'*70}")
        print("GENERATED OBJECTIVES:")
        for obj_type in all_objectives.keys():
            req_count = len(all_objectives[obj_type]["required_fields"])
            opt_count = len(all_objectives[obj_type]["optional_fields"])
            print(f"  - {obj_type}: {req_count} required, {opt_count} optional")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to write config file: {e}")
        return False


def main():
    """Main entry point for the config generator."""
    print("\n[*] Objective Config Generator")
    print("=" * 70)
    
    success = generate_config()
    
    if success:
        print("[SUCCESS] Configuration generated successfully!")
        exit(0)
    else:
        print("[ERROR] Configuration generation failed!")
        exit(1)


if __name__ == "__main__":
    main()

