# Environment Variables Setup Guide

## Current Environment Status

### Successfully Set Variables
The following environment variables have been configured for your AppSignal and OpenTelemetry setup:

```bash
export push_api_key="b9484e99-79b4-4341-ad99-1c264ad5cd93"
export app_name="diamondnode"
export environment="production"
export APPSIGNAL_API_KEY="b9484e99-79b4-4341-ad99-1c264ad5cd93"
```

## Configuration Files

### User-Specific Configuration
**File**: `~/.bashrc`
**Variables**: All four environment variables added
**Scope**: Current user only

### System-Wide Configuration  
**File**: `/etc/profile.d/appsignal.sh`
**Variables**: `APPSIGNAL_API_KEY` (attempted, may require sudo)
**Scope**: All users on the system

## How to Use

### For Current Session
The variables are already set in your current session and can be used immediately:

```bash
# Test that variables are set
echo "APPSIGNAL_API_KEY: $APPSIGNAL_API_KEY"
echo "app_name: $app_name"
echo "environment: $environment"
```

### For New Terminal Sessions
To load the variables in new terminal sessions:

```bash
# Load user-specific variables
source ~/.bashrc

# Load system-wide variables (if available)
source /etc/profile.d/appsignal.sh
```

### For Scripts and Applications
Use the variables directly in your code:

**Bash/Shell:**
```bash
#!/bin/bash
echo "Using API key: $APPSIGNAL_API_KEY"
```

**Python:**
```python
import os
api_key = os.environ['APPSIGNAL_API_KEY']
app_name = os.environ['app_name']
environment = os.environ['environment']
```

**Go:**
```go
apiKey := os.Getenv("APPSIGNAL_API_KEY")
appName := os.Getenv("app_name")
env := os.Getenv("environment")
```

## Testing the Setup

### Quick Test
Run the test script to verify everything is working:

```bash
bash /home/diamondnode/test_environment.sh
```

### Manual Test
```bash
# Test OpenTelemetry directly
cd /home/diamondnode/opentelemetry-go
export PATH=$PATH:$HOME/go/bin
export GOPATH=$HOME/go
export GO111MODULE=on
export GOTOOLCHAIN=go1.25.10
export APPSIGNAL_API_KEY="b9484e99-79b4-4341-ad99-1c264ad5cd93"
./opentelemetry-demo
```

## Expected Output

When everything is working correctly, you should see:

```
2026/05/12 07:49:37 OpenTelemetry initialized successfully
```

## Troubleshooting

### Variables Not Found
If you get "variable not set" errors:

1. **Check if variables are in your bashrc:**
   ```bash
   grep -i "appsignal\|push_api\|app_name" ~/.bashrc
   ```

2. **Reload your bashrc:**
   ```bash
   source ~/.bashrc
   ```

3. **Set variables manually:**
   ```bash
   export APPSIGNAL_API_KEY="b9484e99-79b4-4341-ad99-1c264ad5cd93"
   export app_name="diamondnode"
   export environment="production"
   ```

### Permission Issues
If you need to set system-wide variables but get permission errors:

```bash
# Option 1: Use sudo with a text editor
sudo nano /etc/profile.d/appsignal.sh

# Option 2: Use tee with sudo
 echo "export APPSIGNAL_API_KEY='b9484e99-79b4-4341-ad99-1c264ad5cd93'" | sudo tee -a /etc/profile.d/appsignal.sh

# Option 3: Ask system administrator
```

### OpenTelemetry Not Working
If OpenTelemetry fails to initialize:

1. **Check API key is set:**
   ```bash
   echo $APPSIGNAL_API_KEY
   ```

2. **Check Go environment:**
   ```bash
   go version
   echo $GOPATH
   ```

3. **Rebuild the application:**
   ```bash
   cd /home/diamondnode/opentelemetry-go
   go build -o opentelemetry-demo
   ```

## Variable Reference

| Variable | Value | Purpose |
|-----------|-------|---------|
| `APPSIGNAL_API_KEY` | `b9484e99-79b4-4341-ad99-1c264ad5cd93` | AppSignal authentication |
| `app_name` | `diamondnode` | Application identifier |
| `environment` | `production` | Deployment environment |
| `push_api_key` | `b9484e99-79b4-4341-ad99-1c264ad5cd93` | Alternative API key reference |

## Security Notes

1. **Never expose API keys**: Don't commit these variables to version control
2. **Restrict access**: Keep configuration files secure (600 permissions)
3. **Rotate keys**: Change API keys periodically for security
4. **Use environment variables**: Always prefer environment variables over hardcoding

## Files Created/Modified

### Created Files
- `/home/diamondnode/test_environment.sh` - Environment test script
- `/home/diamondnode/ENVIRONMENT_SETUP.md` - This documentation

### Modified Files
- `~/.bashrc` - Added environment variable exports
- `/etc/profile.d/appsignal.sh` - System-wide configuration (attempted)

## Quick Start

```bash
# 1. Load environment variables
source ~/.bashrc

# 2. Test the setup
bash /home/diamondnode/test_environment.sh

# 3. Use in your applications
cd /home/diamondnode/opentelemetry-go
./opentelemetry-demo
```

## Support

For issues with environment variables:
- Check variable spelling and case sensitivity
- Verify file permissions
- Ensure proper sourcing of configuration files
- Test with manual export if needed

The setup is complete and ready for use with all AI models and applications on this server!