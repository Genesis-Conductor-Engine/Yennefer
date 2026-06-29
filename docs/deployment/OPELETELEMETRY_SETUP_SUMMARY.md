# OpenTelemetry & AppSignal Setup Summary

## Overview
This document summarizes the complete OpenTelemetry setup with AppSignal integration for the diamondnode server.

## What Was Accomplished

### 1. Go Language Setup
- **Installed**: Go 1.22.3 (auto-upgraded to 1.25.10 for compatibility)
- **Location**: `/home/diamondnode/go/`
- **PATH Configuration**: Added to `~/.bashrc`
- **Environment**: `GOPATH`, `GO111MODULE`, `GOTOOLCHAIN` properly configured

### 2. OpenTelemetry Implementation

#### Core Components
- **Tracing**: OTLP trace exporter with batching
- **Metrics**: OTLP metric exporter with periodic reader  
- **Logs**: OTLP log exporter with batch processor
- **Resource Attributes**: Comprehensive AppSignal configuration

#### Project Structure
```
/home/diamondnode/opentelemetry-go/
├── go.mod              # Go module definition
├── go.sum              # Dependency checksums
├── main.go             # Main OpenTelemetry setup
├── main_test.go        # Test suite
└── opentelemetry-demo  # Compiled binary
```

### 3. AppSignal Configuration

#### Resource Attributes
- **Application Name**: `diamondnode`
- **Environment**: `production`
- **API Key**: Loaded from `APPSIGNAL_API_KEY` environment variable
- **Endpoint**: `14g2tvpd.eu-central.appsignal-collector.net`
- **Service Name**: `My service name`
- **Automatic Detection**: Git revision, hostname, app path

#### Security Features
- **API Key Management**: Secure environment variable setup
- **Access Control**: Restricted file permissions (600)
- **Multi-language Support**: Go, Python, Shell access methods

### 4. Security & Access Setup

#### Environment Variable Configuration
- **System-wide**: `/etc/profile.d/appsignal.sh`
- **User-specific**: `~/.bashrc`, `~/.profile`
- **Service configuration**: `/etc/appsignal.env` (restricted to root)

#### Access Methods

**Shell/Bash:**
```bash
echo $APPSIGNAL_API_KEY
# or
get_appsignal_key
```

**Python:**
```python
from appsignal_config import get_appsignal_api_key
api_key = get_appsignal_api_key()
```

**Go:**
```go
apiKey := os.Getenv("APPSIGNAL_API_KEY")
```

**Systemd Services:**
```ini
[Service]
EnvironmentFile=/etc/appsignal.env
```

### 5. Helper Scripts & Tools

#### Setup Script
- **Location**: `/home/diamondnode/setup_appsignal_env.sh`
- **Purpose**: Automated AppSignal API key configuration
- **Features**:
  - Interactive API key input
  - System-wide environment setup
  - Secure file permissions
  - Multi-language support
  - Documentation generation

#### Helper Script
- **Location**: `/usr/local/bin/get_appsignal_key`
- **Purpose**: Secure API key retrieval for scripts
- **Permissions**: 755 (executable by all)

#### Python Module
- **Location**: `/usr/local/lib/python3.10/dist-packages/appsignal_config.py`
- **Functions**:
  - `get_appsignal_api_key()` - Retrieve API key
  - `configure_opentelemetry()` - Full OTel configuration

### 6. Testing & Validation

#### Test Results
- **Build Status**: ✅ Successful
- **Runtime Status**: ✅ Working
- **Test Coverage**: ✅ Basic tracing tests pass
- **Error Handling**: ✅ API key validation implemented

#### Test Commands
```bash
# Build the application
cd /home/diamondnode/opentelemetry-go
export APPSIGNAL_API_KEY="your-api-key-here"
go build -o opentelemetry-demo

# Run the application
./opentelemetry-demo

# Run tests
go test -v
```

### 7. Documentation

#### Files Created
- `/home/diamondnode/APPSIGNAL_SETUP.md` - API key usage guide
- `/home/diamondnode/OPELETELEMETRY_SETUP_SUMMARY.md` - This file

#### Key Information
- **API Key Security**: Never commit to version control
- **File Permissions**: `/etc/appsignal.env` is 600 (root only)
- **Access Control**: Helper script provides controlled access
- **Troubleshooting**: Comprehensive guide in APPSIGNAL_SETUP.md

## Usage Instructions

### For AI Models & Applications

#### Python AI Models
```python
from appsignal_config import configure_opentelemetry

# Get OpenTelemetry configuration
config = configure_opentelemetry()

# Use in your OpenTelemetry setup
resource = Resource.create({
    "appsignal.config.name": "diamondnode",
    "appsignal.config.push_api_key": config['api_key'],
    "appsignal.config.environment": config['environment'],
    # ... other attributes
})
```

#### Go Applications
```go
// Import the initOpenTelemetry function from main.go
cleanup := initOpenTelemetry()
defer cleanup()

// The API key is automatically loaded from environment variable
```

#### Shell Scripts
```bash
#!/bin/bash

# Get API key
API_KEY=$(get_appsignal_key)

# Use in your scripts
echo "Using AppSignal API Key: $API_KEY"
```

### For System Services

#### Systemd Service Example
```ini
[Unit]
Description=My AI Service with OpenTelemetry
After=network.target

[Service]
EnvironmentFile=/etc/appsignal.env
ExecStart=/usr/bin/python3 /path/to/your/ai_service.py
User=diamondnode
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Best Practices

### API Key Management
1. **Never hardcode**: Always use environment variables
2. **Restrict access**: `/etc/appsignal.env` is root-only (600)
3. **No version control**: Add `*.env` to `.gitignore`
4. **Rotate regularly**: Change API keys periodically

### File Permissions
```bash
# Secure environment file
sudo chmod 600 /etc/appsignal.env
sudo chown root:root /etc/appsignal.env

# Secure helper script
sudo chmod 755 /usr/local/bin/get_appsignal_key
sudo chown root:root /usr/local/bin/get_appsignal_key
```

## Troubleshooting

### Common Issues

**API Key Not Found:**
```bash
# Check if environment variable is set
echo $APPSIGNAL_API_KEY

# Source the environment files
source ~/.bashrc
source /etc/profile.d/appsignal.sh

# Check file permissions
ls -la /etc/appsignal.env
```

**Permission Denied:**
```bash
# Fix environment file permissions
sudo chmod 600 /etc/appsignal.env
sudo chown root:root /etc/appsignal.env
```

**Go Module Issues:**
```bash
# Clean and rebuild go modules
cd /home/diamondnode/opentelemetry-go
export GOTOOLCHAIN=go1.25.10
go mod tidy
go build
```

## Next Steps

### Integration Options
1. **Add Gin Web Framework**: Uncomment and implement the Gin middleware
2. **Add Request Logging**: Implement the `recordParameters` function
3. **Add Custom Metrics**: Extend the metrics collection
4. **Add Custom Spans**: Enhance tracing with business logic

### Monitoring Setup
1. **Verify Data Flow**: Check AppSignal dashboard for incoming data
2. **Set Up Alerts**: Configure alerts in AppSignal
3. **Performance Tuning**: Adjust batch sizes and export intervals
4. **Log Correlation**: Ensure logs are properly correlated with traces

### Scaling
1. **Multiple Services**: Create separate configurations for each service
2. **Environment Separation**: Use different API keys for dev/staging/prod
3. **Resource Limits**: Adjust based on server capacity
4. **Sampling**: Implement sampling for high-volume services

## Files Modified/Created

### Modified Files
- `/home/diamondnode/.bashrc` - Added Go PATH
- `/home/diamondnode/opentelemetry-go/main.go` - Updated to use env variable

### Created Files
- `/home/diamondnode/go/` - Go installation
- `/home/diamondnode/opentelemetry-go/` - Project directory
- `/etc/appsignal.env` - Secure API key storage (600)
- `/etc/profile.d/appsignal.sh` - System-wide environment
- `/usr/local/bin/get_appsignal_key` - Helper script (755)
- `/usr/local/lib/python3.10/dist-packages/appsignal_config.py` - Python module
- `/home/diamondnode/setup_appsignal_env.sh` - Setup script (755)
- `/home/diamondnode/APPSIGNAL_SETUP.md` - Documentation
- `/home/diamondnode/OPELETELEMETRY_SETUP_SUMMARY.md` - This file

## Commands Summary

### Setup Commands
```bash
# Run the setup script (as root)
sudo bash /home/diamondnode/setup_appsignal_env.sh

# Source the environment
source ~/.bashrc
source /etc/profile.d/appsignal.sh
```

### Build & Run Commands
```bash
# Navigate to project
cd /home/diamondnode/opentelemetry-go

# Set environment
export PATH=$PATH:$HOME/go/bin
export GOPATH=$HOME/go
export GO111MODULE=on
export GOTOOLCHAIN=go1.25.10
export APPSIGNAL_API_KEY="your-api-key-here"

# Build and run
go build -o opentelemetry-demo
./opentelemetry-demo
```

### Test Commands
```bash
# Run tests
go test -v

# Test API key access
get_appsignal_key
python3 -c "from appsignal_config import get_appsignal_api_key; print(get_appsignal_api_key())"
```

## Support

For issues with:
- **OpenTelemetry**: Check Go documentation and AppSignal docs
- **API Key Issues**: Verify environment setup and file permissions
- **Build Issues**: Check Go version and module compatibility
- **Runtime Issues**: Check network connectivity to AppSignal endpoint

## Conclusion

The OpenTelemetry setup is complete and ready for production use. All AI models and applications on this server can now access the AppSignal API key securely through environment variables, and the OpenTelemetry configuration will automatically send traces, metrics, and logs to AppSignal for comprehensive monitoring and observability.