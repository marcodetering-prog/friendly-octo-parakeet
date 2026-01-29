# Docker Setup for Craftsman Coverage Analyzer

Run the analyzer in a containerized environment with Docker and Docker Compose.

## Prerequisites

- Docker installed and running
- Docker Compose (version 3.8+)
- CSV files in `input/` folder OR Google Sheets credentials set up

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and run the analyzer
docker-compose up

# Or build without running
docker-compose build

# Run with output
docker-compose run craftsman-analyzer
```

### Option 2: Using Docker Directly

```bash
# Build image
docker build -t craftsman-analyzer:latest .

# Run container
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  craftsman-analyzer:latest
```

## File Structure

```
project-root/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Compose configuration
├── google_sheets_analyzer.py
├── requirements.txt
├── input/                  # Mount point for CSV files (read-only)
│   ├── properties.csv
│   └── craftsman.csv
└── output/                 # Mount point for generated reports
    ├── craftsman_coverage_report_*.json
    └── craftsman_coverage_report_*.csv
```

## Usage

### With CSV Files

1. Place your CSV files in the `input/` folder:
   ```
   input/properties.csv
   input/craftsman.csv
   ```

2. Run the container:
   ```bash
   docker-compose up
   ```

3. Reports are generated in the `output/` folder

### With Google Sheets

1. Place `credentials.json` in the project root

2. The credentials are mounted as read-only in the container

3. Update `google_sheets_analyzer.py` with your sheet IDs if needed

4. Run the container:
   ```bash
   docker-compose up
   ```

## Container Details

### Image

- **Base Image**: Python 3.12-slim
- **Size**: ~150-200MB (including dependencies)
- **Multi-stage build**: Reduces final image size by excluding build tools

### Volumes

| Local Path | Container Path | Mode | Purpose |
|-----------|-----------------|------|---------|
| `./input` | `/app/input` | Read-only | Input CSV files |
| `./output` | `/app/output` | Read-write | Generated reports |
| `./credentials.json` | `/app/credentials.json` | Read-only | Google Sheets auth |

### Environment Variables

- `PYTHONUNBUFFERED=1` - Unbuffered output for real-time logs
- `PYTHONDONTWRITEBYTECODE=1` - Don't generate .pyc files
- `PYTHONOPTIMIZE=1` - Enable Python optimizations (optional)

### Health Check

Built-in health check runs every 30 seconds to verify container status.

## Common Commands

```bash
# Run analysis and display output
docker-compose run craftsman-analyzer

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Remove containers and images
docker-compose down --rmi all

# Rebuild image
docker-compose build --no-cache

# Run with custom environment
docker-compose run -e PYTHONOPTIMIZE=0 craftsman-analyzer
```

## Performance Tuning

### Resource Limits

Uncomment the resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Input Size Recommendations

- **Small** (<100 properties): 256MB memory
- **Medium** (100-1000 properties): 512MB memory
- **Large** (>1000 properties): 1GB+ memory

## Troubleshooting

### "No properties found" error

- Verify CSV files exist in `input/` folder
- Check file permissions (should be readable)
- Validate CSV format matches requirements

### "Cannot find credentials.json"

- For CSV mode: Not required
- For Google Sheets: Place credentials in project root
- Verify file path and permissions

### Container exits immediately

Check logs:
```bash
docker-compose logs craftsman-analyzer
```

Common causes:
- Invalid CSV format
- Missing input files
- Python dependency issues

### Slow processing

- Check system resources available to Docker
- Consider increasing memory allocation in `docker-compose.yml`
- Profile using: `docker stats`

## Building for Different Platforms

To build for multiple architectures (requires buildx):

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t craftsman-analyzer:latest \
  .

# Build and push to registry
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/craftsman-analyzer:latest \
  --push .
```

## Security

- Input files mounted as read-only
- Credentials file mounted as read-only
- Container runs with restricted permissions
- No privileged access required

## Notes

- Reports are timestamped to avoid conflicts
- Container exits after completion (not a long-running service)
- All temporary files are cleaned up automatically
- Python bytecode is not written to avoid cache issues

## License

See LICENSE file in project root.
