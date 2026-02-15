#!/usr/bin/env python3
"""
Script to convert FHIR URN references to resource type-based references.
Converts "urn:uuid:xxxxx" to "ResourceType/xxxxx" format.
"""

import json
import os
import re
from pathlib import Path


def build_uuid_to_resource_type_map(data):
    """
    Build a mapping of UUID to resourceType from the Bundle entries.
    Also build a mapping of identifier values to UUIDs.
    
    Args:
        data: Parsed JSON data (FHIR Bundle)
    
    Returns:
        tuple: (uuid_map, identifier_map) where:
            - uuid_map: Mapping of UUID to resourceType
            - identifier_map: Mapping of identifier value to (resourceType, UUID)
    """
    uuid_map = {}
    identifier_map = {}
    
    if data.get("resourceType") == "Bundle" and "entry" in data:
        for entry in data["entry"]:
            full_url = entry.get("fullUrl", "")
            resource = entry.get("resource", {})
            
            if full_url.startswith("urn:uuid:"):
                uuid = full_url.replace("urn:uuid:", "")
                resource_type = resource.get("resourceType")
                resource_id = resource.get("id")
                
                if resource_type:
                    uuid_map[uuid] = resource_type
                
                # Build identifier mappings
                if resource_type and resource_id:
                    identifiers = resource.get("identifier", [])
                    for identifier in identifiers:
                        if isinstance(identifier, dict):
                            value = identifier.get("value")
                            if value:
                                # Map identifier value to (resourceType, UUID)
                                identifier_map[value] = (resource_type, resource_id)
    
    return uuid_map, identifier_map


def is_uuid_format(id_str):
    """
    Check if a string is in UUID format using regex.
    
    Args:
        id_str: The ID string to check
    
    Returns:
        bool: True if it matches UUID format, False otherwise
    """
    # UUID format: 8-4-4-4-12 hexadecimal characters separated by hyphens
    # Example: 6c0b7f20-5c92-efd9-779b-c9ac40656b44
    uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return bool(re.match(uuid_pattern, id_str))


def replace_references(obj, uuid_map, identifier_map, parent_key=None, organization_id=None, in_eob_care_team=False, in_provenance_agent=False, practitioner_id=None, in_careplan_care_team=False):
    """
    Recursively replace URN references with ResourceType/UUID format.
    Also replaces ResourceType?identifier=URL|UUID references.
    Replaces references using identifier values with actual resource UUIDs.
    Removes reference objects with short (non-UUID) IDs.
    Removes all "period" blocks.
    Removes "valueCodeableConcept" blocks from Observation resources.
    Adds provider reference to ExplanationOfBenefit.careTeam objects.
    Adds "who" reference to Provenance agent objects.
    Validates and cleans CarePlan.careTeam to ensure proper FHIR R4 format.
    
    Args:
        obj: JSON object (dict, list, or primitive)
        uuid_map: Mapping of UUID to resourceType
        identifier_map: Mapping of identifier value to (resourceType, UUID)
        parent_key: The parent key (for tracking context)
        organization_id: The Organization ID to use for provider references
        in_eob_care_team: Whether we're currently inside an ExplanationOfBenefit.careTeam array
        in_provenance_agent: Whether we're currently inside a Provenance agent array
        practitioner_id: The Practitioner ID to use for who references
        in_careplan_care_team: Whether we're currently inside a CarePlan.careTeam array
    
    Returns:
        Modified object with replaced references, or None if should be removed
    """
    if isinstance(obj, dict):
        # Detect if this is an Observation resource
        is_observation = obj.get("resourceType") == "Observation"
        
        # Detect if this is a CarePlan resource
        is_careplan = obj.get("resourceType") == "CarePlan"
        
        # Detect if this is a MedicationRequest resource
        is_medication_request = obj.get("resourceType") == "MedicationRequest"
        
        # Check if this dict contains a reference that should be processed or removed
        if "reference" in obj and isinstance(obj["reference"], str):
            ref_value = obj["reference"]
            
            # Handle urn:uuid: references
            if ref_value.startswith("urn:uuid:"):
                uuid = ref_value.replace("urn:uuid:", "")
                if uuid in uuid_map:
                    resource_type = uuid_map[uuid]
                    obj["reference"] = f"{resource_type}/{uuid}"
                    print(f"  Replaced: {ref_value} -> {obj['reference']}")
                else:
                    print(f"  Warning: UUID not found in map: {uuid}")
            # Handle ResourceType?identifier=URL|UUID references
            elif "?identifier=" in ref_value and "|" in ref_value:
                match = re.match(r'(\w+)\?identifier=([^|]+)\|(.+)', ref_value)
                if match:
                    resource_type = match.group(1)
                    identifier_value = match.group(3)
                    
                    # Check if this identifier value maps to a UUID
                    if identifier_value in identifier_map:
                        mapped_resource_type, mapped_uuid = identifier_map[identifier_value]
                        obj["reference"] = f"{mapped_resource_type}/{mapped_uuid}"
                        print(f"  Replaced: {ref_value} -> {obj['reference']}")
                    else:
                        # Identifier not found in map - remove the reference
                        print(f"  Removing reference with unmapped identifier: {ref_value}")
                        return None
            # Check if reference starts with # (internal reference) - mark for removal
            elif ref_value.startswith("#"):
                print(f"  Removing internal reference: {ref_value}")
                return None  # Mark this object for removal
            # Check if reference has ResourceType/ID format
            elif "/" in ref_value:
                parts = ref_value.split("/", 1)
                if len(parts) == 2:
                    resource_type = parts[0]
                    id_part = parts[1]
                    
                    # Check if ID is a valid UUID
                    if is_uuid_format(id_part):
                        # Valid UUID, keep it
                        pass
                    # Check if ID is an identifier value that maps to a UUID
                    elif id_part in identifier_map:
                        mapped_resource_type, mapped_uuid = identifier_map[id_part]
                        # Verify resource types match (or use the mapped one)
                        obj["reference"] = f"{mapped_resource_type}/{mapped_uuid}"
                        print(f"  Replaced identifier reference: {ref_value} -> {obj['reference']}")
                    else:
                        # Not a UUID and not in identifier map - remove it
                        print(f"  Removing invalid reference: {ref_value}")
                        return None  # Mark this object for removal
        
        # Add provider to ExplanationOfBenefit.careTeam objects (after checking existing references)
        if in_eob_care_team and organization_id and "provider" not in obj:
            obj["provider"] = {
                "reference": f"Organization/{organization_id}"
            }
            print(f"  Added provider reference to ExplanationOfBenefit.careTeam object")
        
        # Clean up CarePlan.careTeam - remove any non-reference fields (FHIR R4 validation)
        if in_careplan_care_team and "reference" in obj:
            # CarePlan.careTeam should only contain reference objects with a 'reference' field
            # Remove any other fields like 'provider', 'display', etc. that don't belong
            valid_keys = {"reference", "display"}  # Only reference and optional display are allowed
            keys_to_remove = [k for k in obj.keys() if k not in valid_keys]
            if keys_to_remove:
                for k in keys_to_remove:
                    del obj[k]
                    print(f"  Removed invalid field '{k}' from CarePlan.careTeam reference")
        
        # Add who to Provenance agent objects (after checking existing references)
        if in_provenance_agent and practitioner_id and "who" not in obj:
            obj["who"] = {
                "reference": f"Practitioner/{practitioner_id}"
            }
            print(f"  Added who reference to Provenance agent")
        
        # Process remaining keys and remove "period" blocks
        keys_to_delete = []
        for key, value in list(obj.items()):
            # Remove all "period" blocks
            if key == "period":
                keys_to_delete.append(key)
                print(f"  Removed 'period' block")
                continue
            
            # Remove "valueCodeableConcept" from Observation resources
            if is_observation and key == "valueCodeableConcept":
                keys_to_delete.append(key)
                print(f"  Removed 'valueCodeableConcept' from Observation")
                continue
            
            # Remove "additionalInstruction" from MedicationRequest.dosageInstruction
            if is_medication_request and key == "dosageInstruction" and isinstance(value, list):
                # Process each dosageInstruction element
                for dosage_item in value:
                    if isinstance(dosage_item, dict) and "additionalInstruction" in dosage_item:
                        del dosage_item["additionalInstruction"]
                        print(f"  Removed 'additionalInstruction' from MedicationRequest.dosageInstruction")
            
            # Detect if this is an ExplanationOfBenefit resource
            is_eob = obj.get("resourceType") == "ExplanationOfBenefit"
            
            # Track if we're entering an ExplanationOfBenefit.careTeam array
            entering_eob_care_team = (key == "careTeam" and isinstance(value, list) and is_eob)
            
            # Track if we're entering a CarePlan.careTeam array
            entering_careplan_care_team = (key == "careTeam" and isinstance(value, list) and is_careplan)
            
            # Track if we're entering a Provenance agent array
            entering_provenance_agent = (key == "agent" and isinstance(value, list) and obj.get("resourceType") == "Provenance")
            
            result = replace_references(value, uuid_map, identifier_map, key, organization_id, entering_eob_care_team, entering_provenance_agent, practitioner_id, entering_careplan_care_team)
            
            # If result is None, mark this key for deletion
            if result is None:
                keys_to_delete.append(key)
                print(f"  Removed key '{key}' with invalid reference")
            elif result is not None:
                obj[key] = result
        
        for key in keys_to_delete:
            del obj[key]
            
    elif isinstance(obj, list):
        # Process list items and filter out None values
        new_list = []
        for item in obj:
            result = replace_references(item, uuid_map, identifier_map, parent_key, organization_id, in_eob_care_team, in_provenance_agent, practitioner_id, in_careplan_care_team)
            if result is not None:
                new_list.append(result)
            else:
                print(f"  Removed object from list")
        return new_list
    
    return obj


def add_coverage_resources(data, organization_id="2befa435-3070-3350-a15c-e43ac1e84b24"):
    """
    Add Coverage resources before each ExplanationOfBenefit resource.
    
    Args:
        data: Parsed JSON data (FHIR Bundle)
        organization_id: The Organization ID to use for payor
    
    Returns:
        Modified data with Coverage resources added
    """
    if data.get("resourceType") != "Bundle" or "entry" not in data:
        return data
    
    # Find the Patient ID from the first Patient resource
    patient_id = None
    for entry in data["entry"]:
        if entry.get("resource", {}).get("resourceType") == "Patient":
            patient_id = entry["resource"].get("id")
            break
    
    if not patient_id:
        print("  Warning: No Patient resource found")
        return data
    
    new_entries = []
    coverage_counter = 1
    
    for entry in data["entry"]:
        resource = entry.get("resource", {})
        
        # If this is an ExplanationOfBenefit, add a Coverage resource before it
        if resource.get("resourceType") == "ExplanationOfBenefit":
            # Generate a unique Coverage ID
            import uuid
            coverage_id = str(uuid.uuid4())
            
            # Create Coverage resource
            coverage_entry = {
                "fullUrl": f"urn:uuid:{coverage_id}",
                "resource": {
                    "resourceType": "Coverage",
                    "id": coverage_id,
                    "status": "active",
                    "beneficiary": {
                        "reference": f"Patient/{patient_id}"
                    },
                    "payor": [
                        {
                            "reference": f"Organization/{organization_id}"
                        }
                    ]
                },
                "request": {
                    "method": "POST",
                    "url": "Coverage"
                }
            }
            
            new_entries.append(coverage_entry)
            print(f"  Added Coverage resource before ExplanationOfBenefit")
            
            # Add insurance reference to the ExplanationOfBenefit
            resource["insurance"] = [
                {
                    "focal": True,
                    "coverage": {
                        "reference": f"Coverage/{coverage_id}"
                    }
                }
            ]
            print(f"  Added insurance reference to ExplanationOfBenefit")
            coverage_counter += 1
        
        new_entries.append(entry)
    
    data["entry"] = new_entries
    return data


def process_json_file(file_path, global_identifier_map=None, organization_id="2befa435-3070-3350-a15c-e43ac1e84b24", practitioner_id="a8cd062d-7100-36d2-96c0-a6a3903991ad"):
    """
    Process a single JSON file to convert URN references.
    
    Args:
        file_path: Path to the JSON file
        global_identifier_map: Global mapping of identifier values to (resourceType, UUID) from all files
        organization_id: The Organization ID to use for provider references
        practitioner_id: The Practitioner ID to use for who references
    """
    print(f"\nProcessing: {file_path.name}")
    
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Build UUID to resourceType mapping and local identifier mapping
        uuid_map, local_identifier_map = build_uuid_to_resource_type_map(data)
        print(f"  Found {len(uuid_map)} UUID mappings")
        print(f"  Found {len(local_identifier_map)} local identifier mappings")
        
        # Merge global identifier map with local identifier map (local takes precedence)
        if global_identifier_map:
            identifier_map = {**global_identifier_map, **local_identifier_map}
            print(f"  Using {len(identifier_map)} total identifier mappings (global + local)")
        else:
            identifier_map = local_identifier_map
        
        # Add Coverage resources before ExplanationOfBenefit resources
        data = add_coverage_resources(data, organization_id)
        
        # Replace references
        modified_data = replace_references(data, uuid_map, identifier_map, organization_id=organization_id, practitioner_id=practitioner_id)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(modified_data, f, indent=2)
        
        print(f"  ✓ Successfully updated {file_path.name}")
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Error parsing JSON: {e}")
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")


def build_global_identifier_map(json_files):
    """
    Build a global identifier mapping from all JSON files.
    
    Args:
        json_files: List of JSON file paths
    
    Returns:
        dict: Global mapping of identifier value to (resourceType, UUID)
    """
    global_identifier_map = {}
    
    print("\nBuilding global identifier mappings from all files...")
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("resourceType") == "Bundle" and "entry" in data:
                for entry in data["entry"]:
                    resource = entry.get("resource", {})
                    resource_type = resource.get("resourceType")
                    resource_id = resource.get("id")
                    
                    if resource_type and resource_id:
                        identifiers = resource.get("identifier", [])
                        for identifier in identifiers:
                            if isinstance(identifier, dict):
                                value = identifier.get("value")
                                if value:
                                    # Map identifier value to (resourceType, UUID)
                                    global_identifier_map[value] = (resource_type, resource_id)
        except Exception as e:
            print(f"  Warning: Error reading {file_path.name} for identifier mapping: {e}")
    
    print(f"  Built global identifier map with {len(global_identifier_map)} entries")
    return global_identifier_map


def create_organization_file(script_dir, organization_id="2befa435-3070-3350-a15c-e43ac1e84b24"):
    """
    Create a separate JSON file with the Organization resource.
    
    Args:
        script_dir: Directory where the file should be created
        organization_id: The Organization ID to use
    """
    organization_file_path = script_dir / "organizationInformation.json"
    
    # Check if file already exists
    if organization_file_path.exists():
        print(f"  Organization file already exists: {organization_file_path.name}")
        return
    
    # Create Organization Bundle
    organization_bundle = {
        "resourceType": "Bundle",
        "type": "batch",
        "entry": [
            {
                "fullUrl": f"urn:uuid:{organization_id}",
                "resource": {
                    "resourceType": "Organization",
                    "id": organization_id,
                    "active": True,
                    "type": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                                    "code": "prov",
                                    "display": "Healthcare Provider"
                                }
                            ]
                        }
                    ],
                    "name": "Healthcare Organization"
                },
                "request": {
                    "method": "POST",
                    "url": "Organization"
                }
            }
        ]
    }
    
    # Write to file
    with open(organization_file_path, 'w', encoding='utf-8') as f:
        json.dump(organization_bundle, f, indent=2)
    
    print(f"  Created Organization file: {organization_file_path.name}")


def main():
    """Main function to process all JSON files in the directory."""
    # Get the directory where the script is located
    script_dir = Path(__file__).parent
    
    print(f"Scanning directory: {script_dir}")
    
    # Find all JSON files in the directory
    json_files = list(script_dir.glob("*.json"))
    
    # Filter out the script's own name if it ends with .json
    json_files = [f for f in json_files if f.name != "convert_references.json"]
    
    if not json_files:
        print("No JSON files found in the directory.")
        return
    
    print(f"Found {len(json_files)} JSON file(s) to process")
    
    # Create Organization file if it doesn't exist
    print("\nChecking Organization resource...")
    create_organization_file(script_dir)
    
    # Build global identifier mapping from all files
    global_identifier_map = build_global_identifier_map(json_files)
    
    print("\n" + "=" * 80)
    
    # Process each JSON file with the global identifier map
    for json_file in json_files:
        process_json_file(json_file, global_identifier_map=global_identifier_map)
    
    print("\n" + "=" * 80)
    print(f"\nProcessing complete! Processed {len(json_files)} file(s).")


if __name__ == "__main__":
    main()
