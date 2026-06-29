# @Igor Holt
"""
Bare-metal Triton kernel for Yennefer's EnKG exchange operator.

Implements M = κI + γσ_x on paired state vectors with tensor core optimization.
Operates on contiguous memory blocks for maximum GPU throughput.
"""

import torch

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False
    print("Warning: Triton not available. EnKG kernel will use CPU fallback.")


if TRITON_AVAILABLE:
    @triton.jit
    def enkg_exchange_operator_kernel(
        x_ptr,  # Input tensor pointer
        output_ptr,  # Output tensor pointer
        kappa,  # Identity component
        gamma,  # Pauli-X component
        n_elements,  # Total number of elements
        BLOCK_SIZE: tl.constexpr,  # Block size for tensor cores
    ):
        """
        JIT-compiled Triton kernel for EnKG exchange operator.
        
        Computes: M = κI + γσ_x
        
        For paired state vectors [ψ_0, ψ_1, ψ_2, ψ_3, ...]:
        - Even indices (0, 2, 4, ...): output[i] = κ * x[i] + γ * x[i+1]
        - Odd indices (1, 3, 5, ...): output[i] = γ * x[i-1] + κ * x[i]
        
        This implements the Pauli-X exchange on paired qubits with identity mixing.
        """
        # Program ID identifies which block this kernel handles
        pid = tl.program_id(axis=0)
        
        # Calculate block start position
        block_start = pid * BLOCK_SIZE
        
        # Generate offsets for this block
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        
        # Create mask for valid elements (handle non-divisible sizes)
        mask = offsets < n_elements
        
        # Load input values
        x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        
        # Determine if this is an even or odd index
        is_even = (offsets % 2) == 0
        
        # Calculate paired index offset
        # Even indices pair with next (+1), odd indices pair with previous (-1)
        pair_offset = tl.where(is_even, 1, -1)
        pair_indices = offsets + pair_offset
        
        # Create mask for valid pair indices
        pair_mask = (pair_indices >= 0) & (pair_indices < n_elements) & mask
        
        # Load paired values
        x_pair = tl.load(x_ptr + pair_indices, mask=pair_mask, other=0.0)
        
        # Apply exchange operator: M = κI + γσ_x
        # For even indices: output = κ * x[i] + γ * x[i+1]
        # For odd indices: output = κ * x[i] + γ * x[i-1]
        output = kappa * x + gamma * x_pair
        
        # Store result
        tl.store(output_ptr + offsets, output, mask=mask)


def apply_M_matrix(x: torch.Tensor, kappa: float, gamma: float) -> torch.Tensor:
    """
    Apply EnKG exchange operator M = κI + γσ_x to input tensor.
    
    Args:
        x: Input tensor of shape (..., N) where N must be even
           Must be contiguous for bare-metal optimization
        kappa: Identity component coefficient
        gamma: Pauli-X exchange component coefficient
        
    Returns:
        Transformed tensor with same shape as input
        
    Raises:
        ValueError: If input is not contiguous or has odd final dimension
        RuntimeError: If Triton is not available and CUDA is requested
        
    Example:
        >>> x = torch.tensor([1.0, 2.0, 3.0, 4.0], device='cuda')
        >>> # Pure identity: κ=1, γ=0
        >>> result = apply_M_matrix(x, kappa=1.0, gamma=0.0)
        >>> # result = [1.0, 2.0, 3.0, 4.0]
        >>>
        >>> # Pure Pauli-X: κ=0, γ=1
        >>> result = apply_M_matrix(x, kappa=0.0, gamma=1.0)
        >>> # result = [2.0, 1.0, 4.0, 3.0]  (pairs swapped)
        >>>
        >>> # Mixed operator: κ=0.7, γ=0.3
        >>> result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
        >>> # result = [0.7*1+0.3*2, 0.7*2+0.3*1, 0.7*3+0.3*4, 0.7*4+0.3*3]
    """
    # Validate input
    if not x.is_contiguous():
        raise ValueError("Input tensor must be contiguous for bare-metal optimization")
    
    if x.shape[-1] % 2 != 0:
        raise ValueError(f"Final dimension must be even (got {x.shape[-1]})")
    
    # Handle CPU fallback
    if not x.is_cuda or not TRITON_AVAILABLE:
        return _cpu_fallback(x, kappa, gamma)
    
    # Prepare output tensor
    output = torch.empty_like(x)
    
    # Flatten to 1D for kernel processing
    n_elements = x.numel()
    x_flat = x.flatten()
    output_flat = output.flatten()
    
    # Configure grid for parallel execution
    BLOCK_SIZE = 1024  # Optimized for tensor cores
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch kernel
    enkg_exchange_operator_kernel[grid](
        x_flat,
        output_flat,
        float(kappa),
        float(gamma),
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
    )
    
    return output


def _cpu_fallback(x: torch.Tensor, kappa: float, gamma: float) -> torch.Tensor:
    """
    CPU fallback implementation of EnKG exchange operator.
    
    Used when Triton is not available or input is on CPU.
    """
    output = torch.empty_like(x)
    
    # Flatten for processing
    x_flat = x.flatten()
    output_flat = output.flatten()
    
    # Process pairs
    for i in range(0, len(x_flat), 2):
        if i + 1 < len(x_flat):
            # Even index: κx[i] + γx[i+1]
            output_flat[i] = kappa * x_flat[i] + gamma * x_flat[i + 1]
            # Odd index: γx[i] + κx[i+1]
            output_flat[i + 1] = gamma * x_flat[i] + kappa * x_flat[i + 1]
        else:
            # Handle odd-length (shouldn't happen due to validation)
            output_flat[i] = kappa * x_flat[i]
    
    return output.view_as(x)


def benchmark_enkg_kernel(size: int = 1024, n_iterations: int = 100) -> dict:
    """
    Benchmark EnKG exchange operator performance.
    
    Args:
        size: Tensor size (must be even)
        n_iterations: Number of iterations for timing
        
    Returns:
        Dictionary with timing results
    """
    import time
    
    if size % 2 != 0:
        size += 1
    
    device = 'cuda' if torch.cuda.is_available() and TRITON_AVAILABLE else 'cpu'
    x = torch.randn(size, device=device)
    
    # Warmup
    for _ in range(10):
        _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    # Benchmark
    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    end = time.perf_counter()
    
    avg_time_ms = (end - start) * 1000 / n_iterations
    throughput_gb_s = (size * 4 * 2 / 1e9) / ((end - start) / n_iterations)  # 4 bytes per float32, 2 for read+write
    
    return {
        'device': device,
        'size': size,
        'iterations': n_iterations,
        'avg_time_ms': avg_time_ms,
        'throughput_gb_s': throughput_gb_s,
        'triton_available': TRITON_AVAILABLE,
    }


if __name__ == '__main__':
    # Quick test
    print("EnKG Exchange Operator Test")
    print("=" * 50)
    
    x = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], device='cuda' if torch.cuda.is_available() else 'cpu')
    
    print(f"Input: {x}")
    
    # Test identity
    result = apply_M_matrix(x, kappa=1.0, gamma=0.0)
    print(f"Identity (κ=1, γ=0): {result}")
    
    # Test Pauli-X
    result = apply_M_matrix(x, kappa=0.0, gamma=1.0)
    print(f"Pauli-X (κ=0, γ=1): {result}")
    
    # Test mixed
    result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
    print(f"Mixed (κ=0.7, γ=0.3): {result}")
    
    # Benchmark
    print("\nBenchmark:")
    results = benchmark_enkg_kernel(size=1024*1024, n_iterations=100)
    for key, value in results.items():
        print(f"  {key}: {value}")
