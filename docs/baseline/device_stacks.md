# NVIDIA GPU & System Technical Stack Report

This report summarizes the hardware capabilities, GPU status, CUDA driver, and the software development stack scanned on this local machine.

---

## 1. GPU Overview (NVIDIA Blackwell)

The system is equipped with a next-generation **NVIDIA Blackwell** architecture GPU.

| Parameter | Details |
| :--- | :--- |
| **GPU Model** | NVIDIA GB10 |
| **Product Brand** | NVIDIA RTX |
| **Architecture** | Blackwell |
| **GPU UUID** | `GPU-53f84f3a-bd26-0a37-f852-4441e168166c` |
| **VBIOS Version** | `9A.0B.1E.00.00` |
| **GPU Temp (Idle)** | **37 °C** (Limit: 58 °C) |
| **Power Draw** | **~4.76 W** |
| **Memory Architecture** | **ATS (Address Translation Services)** / Cohesive Memory <br>*(FB Memory Usage and BAR1 report N/A as system memory is unified/dynamically accessed)* |
| **Driver Version** | `580.159.03` |
| **CUDA Capability (Driver)** | `13.0` |

---

## 2. CUDA & NVIDIA Acceleration Toolkit

The system is configured with CUDA Toolkit 13.0, pointing to `/usr/local/cuda-13.0`.

### Core CUDA Tools & SDK
* **CUDA SDK Version**: `13.0.3`
* **CUDA Compiler (`nvcc`)**: `13.0.88`
* **CUDA Runtime (`cudart`)**: `13.0.96`
* **CUDA C++ Core Compute Libraries (CCCL)**: `13.0.85`
* **Nsight Systems**: `2025.3.2.474`
* **Nsight Compute**: `2025.3.1.4`

### Acceleration Libraries
* **cuBLAS**: `13.1.1.3` (Matrix operations)
* **cuFFT**: `12.0.0.61` (Fast Fourier Transform)
* **cuSPARSE**: `12.6.3.3` (Sparse matrices)
* **cuSOLVER**: `12.0.4.66` (Solvers)
* **cuRAND**: `10.4.0.35` (Random number generation)
* **nvJPEG**: `13.0.1.86` (JPEG decoding/encoding)
* **NPP**: `13.0.1.2` (Performance Primitives)
* **GPUDirect Storage (cufile)**: `1.15.1.6`

### Interconnect & Fabric Management
* **Fabric Manager**: `580.126.20`
* **NvSwitch Library (`libnvidia_nscq`)**: `580.126.20`

---

## 3. Host System & Hardware Configuration

This machine features a highly powerful ARM-based unified architecture, pairing the Blackwell GPU with Grace-style Spark CPU computing cores.

### CPU (ARM aarch64)
* **CPU Model**: **Cortex-X925** (Performance cores) & **Cortex-A725** (Efficiency cores)
* **BIOS Model Name**: `GB10 Spark CPU @ 3.9GHz` (BIOS Family 258)
* **Total Cores**: 20 CPU Cores (running at up to 3.9 GHz)
* **Architecture**: `aarch64` (Little Endian)
* **NUMA Nodes**: 1 (all 20 CPUs mapped to Node 0)

### Host Memory (RAM) & Storage
* **Total System Memory**: **121 GiB** (~128 GB RAM)
  * *Used*: ~4.4 GiB
  * *Free*: ~115 GiB
  * *Swap*: 15 GiB
* **System Storage (`/`)**: **916 GiB** (NVMe SSD)
  * *Available*: 827 GiB free (5% utilized)
* **External Storage (`/mnt/usb`)**: **1.9 TiB**
  * *Available*: 1.9 TiB free (1% utilized)

### Operating System
* **OS**: **Ubuntu 24.04.4 LTS** (Noble Numbat)
* **Kernel/Architecture**: `aarch64`

---

## 4. Software Development Stack

### Compilers & Build Tools
* **GCC**: `13.3.0`
* **Make**: `4.3` (aarch64-unknown-linux-gnu)
* **CMake**: `3.28.3`

### Languages & Runtimes
* **Python**: `3.12.3`
* **Node.js**: `v22.22.0`
* **NPM**: `10.9.4`
* *(Go & Rust are not currently installed in the system PATH)*

### Version Control & Containerization
* **Git**: `2.43.0`
* **Docker**: `29.2.1`
