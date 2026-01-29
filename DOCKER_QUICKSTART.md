# Quick Start with Pre-built Docker Image

No need to install Python or touch the code! Just use the pre-built Docker image.

## Prerequisites

- Docker installed ([get it here](https://www.docker.com/products/docker-desktop))
- CSV files in a local `input/` folder

## Option 1: Pull and Run (Simplest)

```bash
# Create input folder with your CSV files
mkdir -p input
# Place your properties.csv and craftsman.csv in input/

# Create output folder for reports
mkdir -p output

# Run the analyzer using the latest pre-built image
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  ghcr.io/marcodetering/friendly-octo-parakeet:latest

# Reports are now in ./output/
```

## Option 2: Using docker-compose (Easier)

Create a `docker-compose.yml` file in your working directory:

```yaml
version: '3.8'
services:
  analyzer:
    image: ghcr.io/marcodetering/friendly-octo-parakeet:latest
    volumes:
      - ./input:/app/input:ro
      - ./output:/app/output:rw
    restart: "no"
```

Then run:

```bash
# Set up folders
mkdir -p input output
# Add your CSV files to input/

# Run
docker-compose up
```

## Available Image Tags

All images are automatically built and pushed to GitHub Container Registry:

| Tag | When Available | Use Case |
|-----|---|---|
| `latest` | On every push to `main` | Latest stable version |
| `main` | On every push | Current main branch |
| `v1.0.0`, `v1.0`, `v1` | On version tags | Specific releases |
| `sha-abc1234` | On every commit | Specific commit |

## Examples

### Example 1: Run Latest Version

```bash
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  ghcr.io/marcodetering/friendly-octo-parakeet:latest
```

### Example 2: Run Specific Version

```bash
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  ghcr.io/marcodetering/friendly-octo-parakeet:v1.0.0
```

### Example 3: Run with Docker Desktop GUI

1. Open Docker Desktop
2. Search for: `ghcr.io/marcodetering/friendly-octo-parakeet`
3. Click "Pull"
4. Once pulled, click "Run"
5. Under "Volumes", mount:
   - `/app/input` → local `input/` folder
   - `/app/output` → local `output/` folder
6. Click "Run"

## File Structure

```
your-project/
├── input/
│   ├── properties.csv
│   └── craftsman.csv
├── output/          (auto-created, contains reports)
│   ├── craftsman_coverage_report_20240129_120000.json
│   └── craftsman_coverage_report_20240129_120000.csv
└── docker-compose.yml (optional)
```

## What You Get

After running, check the `output/` folder for:

- `craftsman_coverage_report_*.json` - Detailed analysis in JSON format
- `craftsman_coverage_report_*.csv` - Coverage gaps in CSV format

Console output shows:
- Summary statistics (total coverage, gaps, categories)
- Properties with full coverage
- Properties with coverage gaps
- Missing properties and unmatched service areas

## Troubleshooting

### "Cannot find input files"
```bash
# Verify files exist
ls -la input/
# Should show: properties.csv and craftsman.csv
```

### "Permission denied"
```bash
# Fix permissions
chmod 644 input/*.csv
```

### "Docker not found"
```bash
# Install Docker: https://www.docker.com/products/docker-desktop
docker --version  # Test installation
```

### Image not found
```bash
# Make sure you're pulling from GitHub Container Registry
# The correct format is: ghcr.io/marcodetering/friendly-octo-parakeet

# Try pulling explicitly
docker pull ghcr.io/marcodetering/friendly-octo-parakeet:latest
```

## Performance

Typical runtime:
- **Small** (< 100 properties): < 5 seconds
- **Medium** (100-1000 properties): 5-30 seconds
- **Large** (> 1000 properties): 30-120 seconds

## Environment Variables

You can optionally set environment variables:

```bash
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  -e PYTHONOPTIMIZE=1 \
  ghcr.io/marcodetering/friendly-octo-parakeet:latest
```

## Updating to Latest Version

```bash
# Pull latest image
docker pull ghcr.io/marcodetering/friendly-octo-parakeet:latest

# Run it
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  ghcr.io/marcodetering/friendly-octo-parakeet:latest
```

## No Code Needed!

You literally don't need to:
- ❌ Clone the repository
- ❌ Install Python
- ❌ Install dependencies
- ❌ Read or modify the code
- ❌ Worry about version conflicts

Just run the Docker command and get your analysis results!

## Need Help?

- Check existing issues: https://github.com/marcodetering/friendly-octo-parakeet/issues
- See full documentation: [DOCKER.md](DOCKER.md)
- View the code: https://github.com/marcodetering/friendly-octo-parakeet

---

**That's it!** Run one command, get your reports. 🎉
