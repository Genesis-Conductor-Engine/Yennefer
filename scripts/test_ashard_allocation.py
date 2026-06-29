#!/usr/bin/env python3
"""
aSHARD Allocation Test
Tests VRAM allocation, Triton kernel execution, and thermal monitoring
"""
import sys
import time
import yaml
from pathlib import Path

def load_config():
    """Load aSHARD configuration"""
    config_path = Path(__file__).parent.parent / "config" / "ashard_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

def check_thermal(config):
    """Check GPU temperature via pynvml"""
    try:
        import pynvml
        pynvml.nvmlInit()
        
        device_name = config["ashard"]["device"]
        device_idx = int(device_name.split(":")[1])
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_idx)
        
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        
        thermal_config = config["ashard"]["thermal"]
        status = "OK"
        
        if temp >= thermal_config["critical_threshold"]:
            status = "CRITICAL"
        elif temp >= thermal_config["warn_threshold"]:
            status = "WARNING"
        
        pynvml.nvmlShutdown()
        
        return {"temperature": temp, "status": status, "unit": "°C"}
    except Exception as e:
        return {"error": str(e)}

def test_allocation(config):
    """Test VRAM allocation per config"""
    import torch
    
    ashard_config = config["ashard"]
    device = torch.device(ashard_config["device"])
    
    print(f"Testing allocation on {device}")
    print(f"Total configured VRAM: {ashard_config['vram_total'] / 1024**3:.2f} GB\n")
    
    allocations = ashard_config["vram_allocation"]
    tensors = {}
    
    try:
        # Check initial VRAM
        torch.cuda.empty_cache()
        initial_allocated = torch.cuda.memory_allocated(device)
        initial_reserved = torch.cuda.memory_reserved(device)
        
        print(f"Initial state:")
        print(f"  Allocated: {initial_allocated / 1024**2:.2f} MB")
        print(f"  Reserved: {initial_reserved / 1024**2:.2f} MB\n")
        
        # Allocate each component
        for name, size_bytes in allocations.items():
            print(f"Allocating {name}: {size_bytes / 1024**3:.2f} GB")
            
            # Allocate tensor of appropriate size
            # float32 = 4 bytes, so divide by 4 to get number of elements
            num_elements = size_bytes // 4
            tensor = torch.zeros(num_elements, dtype=torch.float32, device=device)
            tensors[name] = tensor
            
            allocated = torch.cuda.memory_allocated(device)
            print(f"  Allocated: {allocated / 1024**3:.2f} GB")
        
        print("\nAll allocations successful!")
        
        # Check thermal
        thermal = check_thermal(config)
        print(f"\nGPU Temperature: {thermal.get('temperature', 'N/A')} °C")
        print(f"Thermal Status: {thermal.get('status', 'UNKNOWN')}")
        
        # Test simple operation
        print("\nTesting GPU operations...")
        
        # Use a small test tensor, not the full allocation
        test_size = 1024 * 1024  # 1M elements = 4MB
        test_tensor = torch.zeros(test_size, dtype=torch.float32, device=device)
        
        # Simple operations
        result = test_tensor + 1.0
        result = result * 2.0
        result = torch.sqrt(torch.abs(result))
        
        print("✓ Basic tensor operations successful")
        
        # Clean up test tensor
        del test_tensor
        del result
        
        # Clean up
        print("\nCleaning up...")
        for name in list(tensors.keys()):
            del tensors[name]
        
        torch.cuda.empty_cache()
        final_allocated = torch.cuda.memory_allocated(device)
        
        print(f"Final allocated: {final_allocated / 1024**2:.2f} MB")
        
        # PyTorch may keep some memory cached for performance - allow up to 1GB residual
        if final_allocated < 1024 * 1024**2:  # Within 1GB
            print("✓ Memory released successfully")
            return True
        else:
            print("⚠ Some memory not released")
            return False
        
    except torch.cuda.OutOfMemoryError as e:
        print(f"\n✗ OUT OF MEMORY: {e}")
        print("\nTrying to recover...")
        
        for name in list(tensors.keys()):
            del tensors[name]
        torch.cuda.empty_cache()
        
        return False
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        
        for name in list(tensors.keys()):
            del tensors[name]
        torch.cuda.empty_cache()
        
        return False

def test_triton_kernel(config):
    """Test simple Triton kernel execution"""
    try:
        import torch
        import triton
        import triton.language as tl
        
        @triton.jit
        def add_kernel(
            x_ptr, y_ptr, output_ptr,
            n_elements,
            BLOCK_SIZE: tl.constexpr,
        ):
            pid = tl.program_id(axis=0)
            block_start = pid * BLOCK_SIZE
            offsets = block_start + tl.arange(0, BLOCK_SIZE)
            mask = offsets < n_elements
            x = tl.load(x_ptr + offsets, mask=mask)
            y = tl.load(y_ptr + offsets, mask=mask)
            output = x + y
            tl.store(output_ptr + offsets, output, mask=mask)
        
        device = torch.device(config["ashard"]["device"])
        size = 1024 * 1024  # 1M elements
        
        x = torch.randn(size, device=device)
        y = torch.randn(size, device=device)
        output = torch.zeros(size, device=device)
        
        block_size = config["ashard"]["block_size"]
        grid = lambda meta: (triton.cdiv(size, meta['BLOCK_SIZE']),)
        
        print(f"Testing Triton kernel (block_size={block_size})...")
        
        add_kernel[grid](x, y, output, size, BLOCK_SIZE=block_size)
        
        # Verify result
        expected = x + y
        if torch.allclose(output, expected):
            print("✓ Triton kernel execution successful")
            return True
        else:
            print("✗ Triton kernel produced incorrect results")
            return False
        
    except ImportError:
        print("⚠ Triton not installed, skipping kernel test")
        return None
    except Exception as e:
        print(f"✗ Triton kernel test failed: {e}")
        return False

def test_gateway_integration(config):
    """Test Diamond Gateway metrics integration"""
    import requests
    import os
    
    gateway_config = config["ashard"]["gateway"]
    metrics_url = gateway_config["metrics_url"]
    
    # Check if we have auth token
    auth_var = gateway_config["auth_env_var"]
    token = os.getenv(auth_var)
    
    if not token:
        print(f"⚠ {auth_var} not set, skipping gateway test")
        return None
    
    try:
        print(f"Testing gateway connection to {metrics_url}")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(metrics_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"✓ Gateway metrics retrieved")
            print(f"  VRAM Used: {metrics.get('vram_used_mib', 'N/A')} MiB")
            print(f"  VRAM Total: {metrics.get('vram_total_mib', 'N/A')} MiB")
            print(f"  Temperature: {metrics.get('temperature', 'N/A')} °C")
            return True
        else:
            print(f"✗ Gateway returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Gateway connection failed: {e}")
        return False

def main():
    print("=== aSHARD Allocation Test ===\n")
    
    try:
        config = load_config()
        print("✓ Config loaded\n")
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return 1
    
    # Test 1: Check thermal before starting
    print("--- Thermal Check ---")
    thermal = check_thermal(config)
    if "error" not in thermal:
        temp = thermal["temperature"]
        status = thermal["status"]
        max_temp = config["ashard"]["max_temperature"]
        
        print(f"GPU Temperature: {temp} °C (max: {max_temp} °C)")
        print(f"Status: {status}\n")
        
        if status == "CRITICAL":
            print("✗ GPU too hot, aborting test")
            return 1
    else:
        print(f"⚠ Could not check temperature: {thermal['error']}\n")
    
    # Test 2: VRAM allocation
    print("--- VRAM Allocation Test ---")
    allocation_ok = test_allocation(config)
    print()
    
    if not allocation_ok:
        print("✗ Allocation test failed")
        return 1
    
    # Test 3: Triton kernel (optional)
    print("--- Triton Kernel Test ---")
    triton_ok = test_triton_kernel(config)
    print()
    
    # Test 4: Gateway integration (optional)
    print("--- Gateway Integration Test ---")
    gateway_ok = test_gateway_integration(config)
    print()
    
    # Summary
    print("=== Test Summary ===")
    print(f"Allocation: {'✓ PASS' if allocation_ok else '✗ FAIL'}")
    
    if triton_ok is not None:
        print(f"Triton Kernel: {'✓ PASS' if triton_ok else '✗ FAIL'}")
    
    if gateway_ok is not None:
        print(f"Gateway: {'✓ PASS' if gateway_ok else '✗ FAIL'}")
    
    return 0 if allocation_ok else 1

if __name__ == "__main__":
    sys.exit(main())
