# FHIR Server

A comprehensive FHIR R4 server implementation built with Ballerina, featuring built-in H2 database support or Postgres.

## Features

### Core FHIR API Support
- **CRUD Operations**: Create, Read, Update, Delete for FHIR R4 resources
- **History Tracking**: Resource version history with `_history` endpoint support
- **Search Capabilities**: Advanced search with query parameters

### Custom Profiling
- **StructureDefinition**: Create and manage custom FHIR profiles
- **Custom SearchParameters**: Define domain-specific search parameters
- **Resource Creation**: Validate resources against custom profiles

### FHIR Operations
- **$validate**: Validate any FHIR resource against profiles and constraints
- **$everything**: Retrieve complete patient record (Patient, Encounter, Observation, etc.)
- **$summary**: Generate International Patient Summary (IPS) for patients
- **$export**: Bulk data export for patient resources (NDJSON format)

### Database Support
- **H2 Database**: Built-in embedded database (default configuration)
- **PostgreSQL**: Change configurations in Config.toml

## Quick Start

### Prerequisites

- [Ballerina](https://ballerina.io/downloads/) 2201.13.1 or later
- Java 21 or later
- H2 or Postgre 17 or later

### Starting the Server

**Unix/macOS/Linux:**
```bash
chmod +x start-server.sh
./start-server.sh
```

**Manual start:**
```bash
bal run
```

The server will start on `http://localhost:9090` with H2 database at `./data/fhir-db`.

## Testing with Postman

A complete Postman collection with sample FHIR API requests is available at:
```
scripts/postman-script/FHIR Server.postman_collection.json
```

Import this collection into Postman to quickly test all FHIR operations including CRUD, search, validation, and bulk export.

## Configuration

Edit `Config.toml` to customize the server. Below is the complete configuration template:

```toml
# JDBC Database Configuration for db_handler module
[ballerina_fhir_server.handlers]
# Database type: "h2" or "postgresql"
dbType = "h2"
# Database connection URL
# For H2: 
dbUrl = "jdbc:h2:./data/fhir-db"
dbUser = "sa"
dbPassword = ""
# For PostgreSQL:
# dbType = "postgresql"
# dbUrl = "jdbc:postgresql://localhost:5432/fhir_db"
# dbUser = "<dbUser>"
# dbPassword = "<dbPassword>"
# Set to true to clear all data and reinitialize the database on startup
# Set to false to keep existing data from previous runs
clearDataOnStartup = false

# Resource ID Generation Configuration
[ballerina_fhir_server.utils]
# Database type (MUST match handlers.dbType above)
dbType = "h2"
# If true, the server generates unique IDs for new resources (client-provided IDs are ignored)
# If false, the server uses the ID provided by the client in the resource JSON (if not provided, returns error)
useServerGeneratedIds = false

# Server Base URL Configuration for mappers module
[ballerina_fhir_server.mappers]
baseUrl = "http://localhost:9090"

# International Patient Summary (IPS) Configuration
[ips]
# Organization that maintains/custodian of the IPS documents
custodianOrganization = "Organization/default-hospital"
# Default author/practitioner for IPS documents
authorPractitioner = "Practitioner/system"
# Identifier system for IPS Bundle identifiers (OID or URI)
identifierSystem = "urn:oid:2.16.840.1.113883.2.4.6.3"
# IPS document title
documentTitle = "International Patient Summary"
```

### Key Configuration Options

**Database Type:**
- Both `[ballerina_fhir_server.handlers]` and `[ballerina_fhir_server.utils]` sections must have the **same** `dbType` value
- Supported values: `"h2"` (embedded) or `"postgresql"` (external)

**Database Connection:**
- **H2**: Auto-creates database at `./data/fhir-db` on first run
- **PostgreSQL**: Requires external PostgreSQL server running

**ID Generation:**
- `useServerGeneratedIds = true`: Server auto-generates resource IDs (ignores client-provided IDs)
- `useServerGeneratedIds = false`: Uses client-provided IDs (returns error if missing)

**Clear Data:**
- `clearDataOnStartup = true`: **WARNING** - Deletes all data and reinitializes schema on every server start
- `clearDataOnStartup = false`: Keeps existing data across restarts

## Database Management

### Clear Database on Startup
```toml
[ballerina_fhir_server.handlers]
clearDataOnStartup = true  # WARNING: Deletes all existing data
```

### Manual Schema Initialization

**H2:**
```bash
# Schema is auto-created on first run
# Manual schema: scripts/schema-h2.sql
```

**PostgreSQL:**
```bash
psql -U postgres -d fhir_db -f scripts/schema-postgresql.sql
```

## Switching Database

1. Edit `Config.toml` and change `dbType` in both sections
2. Update connection details
3. Restart server
