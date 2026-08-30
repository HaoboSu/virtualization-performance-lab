# Virtualization Performance Lab

A reproducible systems-performance project investigating how **CPU contention and CPU overcommitment affect workload performance inside virtual machines**.

This repository is designed as an independent research portfolio project in virtualization, performance engineering, and HPC–cloud systems.

> **Status:** Work in progress  
> **Initial study:** CPU contention between two virtual machines sharing the same physical CPU resource

---

## 1. Research Question

**How does CPU contention affect the performance and tail latency of workloads running in virtualized environments?**

The first experiment studies a simple noisy-neighbor scenario:

- **VM1** runs the benchmark workload.
- **VM2** generates controlled CPU load.
- Both virtual machines compete for the same physical CPU resource.
- The contention level is gradually increased.
- VM1 performance is measured under each condition.

The purpose is to observe how workload performance changes as CPU contention increases.

---

## 2. Motivation

Virtualized infrastructure allows multiple virtual machines to share the same physical resources.

This improves utilization, but it can also introduce **resource contention** when several workloads compete for CPU time.

For latency-sensitive or compute-intensive workloads, this interference may lead to:

- longer execution time;
- reduced throughput;
- higher response latency;
- higher tail latency;
- increased context switching;
- increased scheduling overhead;
- less predictable performance.

Understanding these effects is relevant to:

- cloud computing;
- multi-tenant infrastructure;
- resource isolation;
- virtualized HPC environments;
- performance-aware scheduling;
- HPC–cloud convergence.

---

## 3. Initial Hypothesis

The initial hypothesis is:

> Increasing CPU contention is expected to reduce workload throughput and increase execution time and tail latency when multiple virtual machines compete for the same physical CPU resources.

This is a hypothesis to be tested experimentally.  
The project will distinguish **observed associations** from causal conclusions that are not directly supported by the measurements.

---

## 4. Experimental Design

The initial experiment uses two virtual machines on the same physical host.

```text
                  Physical Host
                       |
                Shared CPU Resource
                       |
          +------------+------------+
          |                         |
        VM1                       VM2
   Benchmark VM              Contention VM
          |                         |
   Run workload               Generate load
          |                         |
          +------------+------------+
                       |
               Performance Results
```

### VM1 — Benchmark VM

VM1 runs the workload being measured.

Planned workloads:

1. `sysbench` CPU benchmark
2. a small latency-sensitive benchmark
3. optional extension: the 3D Laplace / Gauss–Seidel solver from my M.Sc. HPC project

### VM2 — Contention VM

VM2 generates controlled synthetic CPU load using `stress-ng`.

Planned contention levels:

| Condition | VM2 CPU Load |
|---|---:|
| Baseline | 0% |
| Light | 25% |
| Medium | 50% |
| High | 75% |
| Heavy | 100% |

---

## 5. Reference VM Configuration

The first version of the experiment is designed around the following reference configuration:

| Setting | VM1 | VM2 |
|---|---:|---:|
| Guest OS | Ubuntu Server 24.04 LTS | Ubuntu Server 24.04 LTS |
| vCPU | 1 | 1 |
| RAM | 4 GB | 4 GB |
| Disk | 20–30 GB | 20–30 GB |
| Network | Local network | Local network |
| Internet during benchmark | Not required | Not required |

### Important CPU Placement Requirement

For the CPU-contention experiment to be meaningful, VM1 and VM2 should compete for the **same physical CPU resource**.

The preferred initial setup is:

```text
Physical CPU Core X
    |
    +---- VM1 vCPU 0
    |
    +---- VM2 vCPU 0
```

This creates a simple CPU-overcommitment scenario in which two virtual CPUs compete for one physical CPU resource.

The exact pinning configuration will depend on the physical host CPU and hypervisor.

---

## 6. Software Environment

Planned guest tools:

```bash
sudo apt update
sudo apt install -y build-essential
sudo apt install -y stress-ng
sudo apt install -y sysbench
sudo apt install -y linux-tools-common
sudo apt install -y python3 python3-pip
```

Additional tools may be added later for monitoring and profiling.

Possible later extensions include:

- `perf`
- Prometheus
- Node Exporter
- Grafana

The first version intentionally keeps the software stack simple.

---

## 7. Benchmark Conditions

The initial experiment compares VM1 performance under five CPU-contention conditions:

```text
0% CPU load on VM2
25% CPU load on VM2
50% CPU load on VM2
75% CPU load on VM2
100% CPU load on VM2
```

Example contention generation:

```bash
stress-ng --cpu 1 --cpu-load 25 --timeout 60s
```

```bash
stress-ng --cpu 1 --cpu-load 50 --timeout 60s
```

```bash
stress-ng --cpu 1 --cpu-load 75 --timeout 60s
```

```bash
stress-ng --cpu 1 --cpu-load 100 --timeout 60s
```

The baseline condition leaves VM2 idle.

---

## 8. Initial Benchmark

The first VM1 benchmark will use `sysbench`:

```bash
sysbench cpu --threads=1 --time=60 run
```

The initial measurements will include the metrics reported by the benchmark, such as:

- events per second;
- total execution time;
- average latency;
- percentile latency where available.

A later stage will add a custom benchmark to collect more explicit latency distributions.

---

## 9. Repetition Strategy

A single benchmark run is not sufficient for reliable comparison.

Each experimental condition will therefore be repeated multiple times.

### Initial plan

**20 repetitions per condition**

With five conditions:

```text
5 contention levels × 20 repetitions = 100 benchmark runs
```

The number of repetitions may be adjusted after a pilot experiment.

---

## 10. Metrics

The initial study will focus on workload-level performance metrics.

### Primary Metrics

- execution time;
- throughput;
- mean latency;
- p95 latency;
- p99 latency, where measurable.

### System-Level Metrics

Later experiments may collect:

- CPU utilization;
- CPU steal time;
- context switches;
- CPU migrations;
- CPU cycles;
- instructions;
- cache misses.

Where supported, these can be collected using tools such as:

```bash
perf stat
```

---

## 11. Planned Analysis

The initial analysis will compare performance against CPU contention level.

Planned plots include:

1. **CPU contention vs execution time**
2. **CPU contention vs throughput**
3. **CPU contention vs p95/p99 latency**
4. optional: **CPU contention vs context switches**

The analysis will report descriptive statistics such as:

- mean;
- median;
- standard deviation;
- minimum;
- maximum;
- percentiles.

Raw measurements will be preserved separately from processed results.

---

## 12. Planned Repository Structure

```text
virtualization-performance-lab/
│
├── README.md
├── LICENSE
│
├── workloads/
│   ├── sysbench/
│   ├── latency-benchmark/
│   └── laplace-solver/
│
├── scripts/
│   ├── run-baseline.sh
│   ├── run-contention.sh
│   ├── run-experiment.sh
│   └── collect-perf.sh
│
├── results/
│   ├── raw/
│   └── processed/
│
├── analysis/
│   └── analyze-results.py
│
├── figures/
│
└── docs/
    ├── experimental-setup.md
    ├── methodology.md
    └── limitations.md
```

The directory structure will be expanded as the experiment develops.

---

## 13. Reproducibility

The project aims to record enough information for the experiment to be reproduced.

The final experimental documentation will include:

- host CPU model;
- host RAM;
- hypervisor and version;
- guest OS version;
- guest kernel version;
- VM vCPU configuration;
- VM memory configuration;
- CPU pinning / affinity settings;
- benchmark versions;
- contention-generator version;
- experiment duration;
- repetition count;
- raw measurement data.

The following template will be completed after the physical test machine is selected:

```text
Host CPU:
Host physical cores:
Host logical CPUs:
Host RAM:
Hypervisor:
Hypervisor version:

VM1:
Guest OS:
Kernel:
vCPU:
RAM:
Disk:

VM2:
Guest OS:
Kernel:
vCPU:
RAM:
Disk:

CPU placement:
VM1 vCPU:
VM2 vCPU:
Shared physical CPU resource:
```

---

## 14. Network Requirements

Internet access is useful during initial setup for package installation.

However, the CPU benchmark itself does **not** require Internet access.

For the formal benchmark runs:

- Internet access is not required;
- both VMs may remain on a local management network;
- VM1 and VM2 do not need to communicate with each other for the initial CPU-contention experiment.

This reduces unnecessary network activity during measurement.

---

## 15. Experimental Controls

To reduce avoidable variation, the first experiment will keep the following factors fixed:

- same guest operating system;
- same kernel version;
- same VM configuration;
- same benchmark version;
- same hypervisor;
- same physical host;
- same CPU placement;
- same benchmark duration;
- same repetition procedure.

The main independent variable is:

> **CPU load generated by VM2**

The main dependent variables are:

> **VM1 workload performance metrics**

---

## 16. Results

**Results have not yet been collected.**

This section will be updated after the first experimental campaign.

Planned result table:

| VM2 CPU Load | Mean Runtime | Throughput | Mean Latency | p95 | p99 |
|---:|---:|---:|---:|---:|---:|
| 0% | TBD | TBD | TBD | TBD | TBD |
| 25% | TBD | TBD | TBD | TBD | TBD |
| 50% | TBD | TBD | TBD | TBD | TBD |
| 75% | TBD | TBD | TBD | TBD | TBD |
| 100% | TBD | TBD | TBD | TBD | TBD |

No performance results will be added until they are experimentally measured.

---

## 17. Current Limitations

The initial experiment is intentionally small in scope.

Current limitations include:

1. **Small-scale environment**  
   The experiment uses only two virtual machines on one physical host.

2. **Synthetic contention**  
   CPU load is generated using `stress-ng` and may not represent every real production workload.

3. **CPU-only first phase**  
   Memory, network, storage, and NUMA interference are outside the initial scope.

4. **Platform dependence**  
   Results may vary with CPU architecture, hypervisor, scheduler behavior, and host configuration.

5. **Limited causal interpretation**  
   Observed performance changes will not automatically be attributed to one specific low-level mechanism unless the experiment directly measures it.

---

## 18. Future Work

Planned extensions include:

### Resource Contention

- memory contention;
- storage contention;
- network contention;
- NUMA effects.

### Virtualization Configuration

- CPU pinning;
- CPU affinity;
- SMT / Hyper-Threading effects;
- different CPU overcommitment ratios;
- scheduler configuration.

### Isolation Comparison

- bare-metal execution;
- Docker containers;
- virtual machines;
- containers inside virtual machines.

### HPC Workloads

- MPI workloads;
- OpenMP workloads;
- the 3D Laplace / Gauss–Seidel solver from my M.Sc. HPC project;
- communication-intensive benchmarks.

### Research Direction

A longer-term goal is to study:

> **performance isolation and resource-aware scheduling for HPC workloads in containerized and virtualized environments.**

---

## 19. Relationship to My Previous Work

This project extends my previous experience in high-performance and virtualized computing.

My M.Sc. project at Trinity College Dublin investigated serial, OpenMP, and MPI implementations of a 3D Laplace solver, including Docker-based execution and strong-scaling analysis.

Related project:

[HaoboSu/hpc-thesis-project](https://github.com/HaoboSu/hpc-thesis-project)

The present project shifts the focus from parallelization itself toward:

- virtualization overhead;
- resource contention;
- workload interference;
- performance isolation;
- systems performance engineering.

---

## 20. Data and Confidentiality

All experiments in this repository will use:

- self-contained test environments;
- synthetic workloads;
- personally controlled virtual machines;
- publicly reproducible configurations.

**No proprietary company infrastructure, production configuration, internal monitoring data, customer information, or confidential system details will be included.**

---

## Author

**Haobo Su**

M.Sc. High Performance Computing — Trinity College Dublin

Research interests:

- High-Performance Computing
- Distributed Systems
- Virtualization
- Containerized Computing
- Performance Engineering
- Resource Isolation
- HPC–Cloud Convergence

GitHub: [HaoboSu](https://github.com/HaoboSu)
