#!/usr/bin/env python3
"""
aSHARD GPU Capability Detection
Detects CUDA availability, VRAM, tensor cores, and validates configuration
"""
import sys
import json
from pathlib import Path

def detect_gpu_capabilities():
    """Detect GPU capabilities and return aSHARD config"""
    result = {
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "recommended_config": None,
        "errors": []
    }
    
    try:
        import torch
    except ImportError:
        result["errors"].append("PyTorch not installed")
        return result
    
    result["cuda_available"] = torch.cuda.is_available()
    
    if not result["cuda_available"]:
        result["errors"].append("CUDA not available")
        return result
    
    result["device_count"] = torch.cuda.device_count()
    
    for i in range(result["device_count"]):
        device_props = torch.cuda.get_device_properties(i)
        device_info = {
            "index": i,
            "name": device_props.name,
            "compute_capability": f"{device_props.major}.{device_props.minor}",
            "total_memory": device_props.total_memory,
            "total_memory_gb": round(device_props.total_memory / (1024**3), 2),
            "multi_processor_count": device_props.multi_processor_count,
            "max_threads_per_block": device_props.max_threads_per_block,
            "max_threads_per_multi_processor": device_props.max_threads_per_multi_processor,
        }
        
        # Tensor core detection (Volta 7.0+, but GTX 1650 is Turing without tensor cores)
        has_tensor_cores = device_props.major >= 7
        # GTX 1650 is compute capability 7.5 but doesn't have tensor cores (GTX vs RTX)
        if "GTX" in device_props.name and "16" in device_props.name:
            has_tensor_cores = False
        
        device_info["tensor_cores"] = has_tensor_cores
        
        result["devices"].append(device_info)
    
    # Generate recommended config for first device
    if result["devices"]:
        device = result["devices"][0]
        total_vram = device["total_memory"]
        
        # Conservative allocation (leave 10% for CUDA overhead)
        usable_vram = int(total_vram * 0.9)
        
        result["recommended_config"] = {
            "device": f"cuda:{device['index']}",
            "vram_total": total_vram,
            "vram_allocation": {
                "enkg_kernel": int(usable_vram * 0.5),  # 50% for kernel
                "orchestration": int(usable_vram * 0.25),  # 25% for orchestration
                "buffer": int(usable_vram * 0.25),  # 25% buffer
            },
            "tensor_cores": device["tensor_cores"],
            "compute_capability": device["compute_capability"],
            "max_threads_per_block": device["max_threads_per_block"],
        }
    
    return result

def validate_config(config_path: Path):
    """Validate aSHARD config against detected hardware"""
    import yaml
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    detection = detect_gpu_capabilities()
    
    if not detection["cuda_available"]:
        return {"valid": False, "errors": ["CUDA not available"]}
    
    errors = []
    warnings = []
    
    ashard_config = config.get("ashard", {})
    device_idx = int(ashard_config.get("device", "cuda:0").split(":")[1])
    
    if device_idx >= detection["device_count"]:
        errors.append(f"Device {device_idx} not found (only {detection['device_count']} devices)")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    device = detection["devices"][device_idx]
    configured_vram = ashard_config.get("vram_total", 0)
    actual_vram = device["total_memory"]
    
    # Check VRAM
    if configured_vram > actual_vram:
        errors.append(
            f"Configured VRAM ({configured_vram / 1024**3:.2f} GB) exceeds "
            f"actual VRAM ({actual_vram / 1024**3:.2f} GB)"
        )
    elif configured_vram < actual_vram * 0.95:
        warnings.append(
            f"Configured VRAM ({configured_vram / 1024**3:.2f} GB) is less than "
            f"available ({actual_vram / 1024**3:.2f} GB)"
        )
    
    # Check tensor cores
    if ashard_config.get("tensor_cores") and not device["tensor_cores"]:
        warnings.append(
            f"Tensor cores enabled in config but not available on {device['name']}"
        )
    
    # Check allocation
    allocation = ashard_config.get("vram_allocation", {})
    total_allocated = sum(allocation.values())
    
    if total_allocated > configured_vram:
        errors.append(
            f"Total allocation ({total_allocated / 1024**3:.2f} GB) exceeds "
            f"configured VRAM ({configured_vram / 1024**3:.2f} GB)"
        )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "device": device,
    }

def main():
    print("=== aSHARD GPU Detection ===\n")
    
    detection = detect_gpu_capabilities()
    
    print(f"CUDA Available: {detection['cuda_available']}")
    print(f"Device Count: {detection['device_count']}\n")
    
    for device in detection["devices"]:
        print(f"Device {device['index']}: {device['name']}")
        print(f"  Compute Capability: {device['compute_capability']}")
        print(f"  Total Memory: {device['total_memory_gb']} GB")
        print(f"  Tensor Cores: {device['tensor_cores']}")
        print(f"  Multi-processors: {device['multi_processor_count']}")
        print(f"  Max Threads/Block: {device['max_threads_per_block']}")
        print()
    
    if detection["errors"]:
        print("ERRORS:")
        for error in detection["errors"]:
            print(f"  - {error}")
        return 1
    
    if detection["recommended_config"]:
        print("Recommended Configuration:")
        print(json.dumps(detection["recommended_config"], indent=2))
        print()
    
    # Validate existing config if present
    config_path = Path(__file__).parent.parent / "config" / "ashard_config.yaml"
    if config_path.exists():
        print(f"Validating config: {config_path}")
        validation = validate_config(config_path)
        
        if validation["valid"]:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has errors:")
            for error in validation["errors"]:
                print(f"  - {error}")
        
        if validation.get("warnings"):
            print("Warnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        return 0 if validation["valid"] else 1
    else:
        print(f"Config file not found: {config_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
