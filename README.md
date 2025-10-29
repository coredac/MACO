# MACO: Multi-Agent CGRA Optimization

MACO is a machine learning-based framework for automated CGRA (Coarse-Grained Reconfigurable Array) architecture design and optimization. It leverages Large Language Models (LLMs) integrated with multiple specialized agents to intelligently explore and evaluate hardware architecture configurations, balancing performance, power consumption, and area constraints.

## Overview

MACO uses a multi-agent system powered by LLMs to automate the generation of optimal CGRA architectures. The framework iteratively generates, evaluates, and refines hardware designs to find optimal configurations for specific computational kernels.

## Project Structure

```
MACO/
├── agent/               # LLM-based agents for design exploration
│   ├── ArchDesigner.py        # CGRA architecture generation
│   ├── Expertjudge.py         # Expert evaluation agent
│   ├── Expertjudge_2.py       # Enhanced evaluation agent
│   ├── Mapfixer.py            # Mapping violation repair
│   └── Heuristic_judge.py     # Rule-based evaluation
├── algorithm/           # Core optimization algorithms
│   ├── algorithm1.py          # Main optimization workflow
│   ├── algorithm2.py          # Design selection logic
│   ├── pipeline.py            # High-level orchestration
│   ├── ex_framework.py        # Experimental framework
│   └── ex_model.py            # Experimental models
├── baseline/            # Baseline implementations
│   ├── qwen_domain_agumented.py
│   └── qwen_few_shot_examples.py
├── verilog_tool/        # Hardware synthesis tools
│   ├── generate_verilog.py    # Verilog RTL generation
│   ├── append_ppa.py          # PPA metric estimation
│   └── arch2dc.bash           # Synthesis script
├── eda_tool/            # EDA tool integration
│   └── arch_sample_sv2v_run.tcl
├── tool/                # Evaluation utilities
│   └── test_process_candidates.py
└── results/             # Output storage
    ├── cgra_best_design.json
    ├── cgra_candidates_raw.json
    ├── cgra_candidates_fixed.json
    ├── cgra_historical_design.json
    └── cgra_top_k.json
```

## Workflow

The MACO optimization pipeline consists of the following stages:

1. **Architecture Generation**: `ArchDesigner` generates initial CGRA design candidates based on kernel specifications and optimization goals
2. **Mapping Repair**: `Mapfixer` corrects any mapping violations to ensure hardware feasibility
3. **Evaluation**: Designs are evaluated by both expert LLM agents (`ExpertJudge`) and heuristic evaluators
4. **Selection**: `DesignSelector` ranks designs using hybrid LLM + tool scoring
5. **Refinement**: Historical feedback is incorporated into the next iteration
6. **Verilog Generation**: Optimal designs are converted to synthesizable RTL

## Components

### Agent Modules

- **ArchDesigner**: Generates CGRA architecture candidates with specified tile configurations, functional units, and memory parameters
- **ExpertJudge**: Evaluates design quality using LLM-based expert reasoning
- **Mapfixer**: Automatically fixes mapping violations (invalid FU placements, memory allocation issues)
- **HeuristicJudge**: Fast evaluation using rule-based heuristics

### Algorithm Modules

- **algorithm1.py**: Main execution pipeline implementing multi-stage design optimization with decaying epsilon-greedy exploration
- **algorithm2.py**: Design selection using unified scoring and adaptive thresholding
- **pipeline.py**: High-level orchestration of the complete workflow

### Verilog Tools

- **generate_verilog.py**: Generates SystemVerilog/Verilog RTL from CGRA design specifications
- **append_ppa.py**: Estimates and appends Performance/Power/Area (PPA) metrics
- **arch2dc.bash**: Synthesis automation script

## Optimization Targets

MACO supports multiple optimization objectives:

- **Performance**: Maximize throughput and parallelism
- **Power**: Minimize power consumption
- **Area**: Reduce hardware resource usage
- **Energy**: Optimize energy efficiency

## Supported LLM Models

- Qwen models (qwen-plus) 
- OpenAI models (GPT-4, GPT-4o)
- DeepSeek models
- Custom API endpoints

## CGRA Design Format

Designs are represented as JSON specifications:

```json
{
  "tile_size": "4x4",
  "FUs": {
    "tile0": ["Ld", "Add"],
    "tile1": ["Mul", "Add"],
    ...
  },
  "config_mem": 128,
  "data_spm_kb": 64,
  "unroll_factor": 2,
  "vectorize": "interleaved",
  "kernel": "path/to/kernel.c"
}
```

## Usage

# Enter your API key in each file that requires it
```python
api_key = "xxxxxxxxxxx"
```

### Running the Pipeline

The main entry point is `pipeline.py`. Configure the kernel type, optimization goal, and model selection in the script:

```python
# Example configuration
kernel = "conv"  # or "fir"
optimization_goal = "performance"  # "performance", "power", "area", "energy"
model = "qwen-plus"
```

Then run:

```bash
python algorithm/pipeline.py
```


## Output Files

Results are stored in the `results/` directory:

- **cgra_best_design.json**: Optimal design(s) identified
- **cgra_candidates_raw.json**: Initial generated candidates
- **cgra_candidates_fixed.json**: Candidates after mapping fixes
- **cgra_historical_design.json**: Historical designs for feedback loops
- **cgra_top_k.json**: Top-K candidate designs


## Citation

If you use MACO in your research, please cite:

MACO: A Multi-Agent LLM-Based Hardware/Software Co-Design Framework for CGRAs

## Contact

zjian137@asu.edu

## Acknowledgments

This project integrates with the VectorCGRA framework(https://github.com/tancheng/VectorCGRA) for hardware synthesis.
