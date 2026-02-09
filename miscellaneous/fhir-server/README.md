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

Edit `Config.toml` to customize the server:

### Database Configuration

**H2 (Default - Embedded):**
```toml
[ballerina_fhir_server.handlers]
dbType = "h2"
dbUrl = "jdbc:h2:./data/fhir-db"
dbUser = "sa"
dbPassword = ""
```

**PostgreSQL (Optional):**
```toml
[ballerina_fhir_server.handlers]
dbType = "postgresql"
dbUrl = "jdbc:postgresql://localhost:5432/fhir_db"
dbUser = "postgres"
dbPassword = "your_password"
```

### ID Generation

```toml
[ballerina_fhir_server.utils]
useServerGeneratedIds = false  # true: server generates IDs, false: use client-provided IDs
```

### IPS Configuration

```toml
[ips]
custodianOrganization = "Organization/default-hospital"
authorPractitioner = "Practitioner/system"
identifierSystem = "urn:oid:2.16.840.1.113883.2.4.6.3"
documentTitle = "International Patient Summary"
```

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
