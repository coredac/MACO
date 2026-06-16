# MACO: A Multi-Agent LLM-Based Hardware/Software Co-Design Framework for CGRAs

MACO is a LLM-based multi-agent system framework for automated CGRA (Coarse-Grained Reconfigurable Array) architecture design and optimization. It leverages Large Language Models (LLMs) integrated with multiple specialized agents to intelligently explore and evaluate hardware architecture configurations, balancing performance, power consumption, and area constraints.

## Overview

MACO uses a multi-agent system powered by LLMs to automate the generation of optimal CGRA architectures. The framework iteratively generates, evaluates, and refines hardware designs to find optimal configurations for specific computational kernels.

## Project Structure

```
MACO/
├── run_maco.py                             # Top-level MACO entrypoint
├── run_maco_experiment.py                  # Per-kernel MACO experiment driver
├── run_single_agent_baseline.py            # Single-agent LLM baseline
├── agent/                                  # The four MACO agents (paper Fig. 4)
│   ├── cgra_codesigner.py                  # Stage 1 — CGRA Co-designer
│   ├── cgra_fixer.py                       # Stage 2 — CGRA Fixer
│   ├── coarse_grained_judge.py             # Stage 3a — Coarse-grained Judge
│   └── fine_grained_judge.py               # Stage 3b — Fine-grained Judge
├── algorithm/                              # MACO core mechanisms
│   ├── exploration_exploitation.py         # ε-greedy ECE mechanism (Sec. III-B)
│   └── confidence_adaptive_selector.py     # Confidence-Adaptive Selection (Sec. III-D)
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

The MACO four-stage iterative loop (paper Sec. III):

1. **Stage 1 — CGRA Design**: `CGRACoDesigner` proposes HW/SW candidate designs, scheduled between exploration and exploitation by the ε-greedy ECE mechanism
2. **Stage 2 — Validation & Correction**: `CGRAFixer` validates each candidate and applies rule-driven syntax / mapping repairs
3. **Stage 3a — Coarse-grained Judge**: `CoarseGrainedJudge` performs an LLM-only top-K screen on the fixed pool
4. **Stage 3b — Fine-grained Judge**: `FineGrainedJudge`, driven by `ConfidenceAdaptiveSelector`, cooperates with EDA tools under an adaptive-confidence scheme and self-learns from the tool feedback
5. **Stage 4 — Evaluation & Feedback**: PPA reports from synthesis are folded back into history for the next iteration
6. **RTL/Synthesis**: best designs are emitted as synthesizable Verilog

## Components

### Agent Modules

- **CGRACoDesigner** (`cgra_codesigner.py`): joint HW/SW candidate generator (Stage 1)
- **CGRAFixer** (`cgra_fixer.py`): rule-driven repair of syntax / mapping errors (Stage 2)
- **CoarseGrainedJudge** (`coarse_grained_judge.py`): LLM-only top-K shortlist (Stage 3a)
- **FineGrainedJudge** (`fine_grained_judge.py`): final single-best selection with self-learning feedback (Stage 3b)

### Mechanism Modules (`algorithm/`)

- **exploration_exploitation.py**: Exponentially decaying ε-greedy ECE mechanism (Sec. III-B) that schedules the multi-iteration loop
- **confidence_adaptive_selector.py**: Confidence-Adaptive Selection + self-learning between the Fine-grained Judge and the EDA tool (Sec. III-D)

### Entry Points (repo root)

- **run_maco.py**: Single-iteration top-level MACO entrypoint
- **run_maco_experiment.py**: Per-kernel MACO experiment driver
- **run_single_agent_baseline.py**: Single-agent LLM baseline used for comparison

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

### Prerequisites

- Python 3.8 or higher
- Synopsys Design Compiler (for synthesis)
- VectorCGRA framework (see installation instructions below)

### Environment Setup

1. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

2. **Install VectorCGRA framework:**

The project requires the VectorCGRA framework for Verilog generation. Please follow the installation instructions at:
https://github.com/tancheng/VectorCGRA

3. **Configure API key:**

The four agent modules read your DashScope API key from the `DASHSCOPE_API_KEY` environment variable — never hardcode it in source. Export it in your shell before running any script:

```bash
export DASHSCOPE_API_KEY="sk-your-api-key-here"
```

Or load it from a local `.env` file (already git-ignored).

### Running the Pipeline

The main entry point is `run_maco.py`. Configure the kernel type, optimization goal, and model selection in the script:

```python
# Example configuration
kernel = "conv"  # or "fir"
optimization_goal = "performance"  # "performance", "power", "area", "energy"
model = "qwen-plus"
```

Then run:

```bash
python3 run_maco.py
```


## Output Files

Results are stored in the `results/` directory:

- **cgra_best_design.json**: Optimal design(s) identified
- **cgra_candidates_raw.json**: Initial generated candidates
- **cgra_candidates_fixed.json**: Candidates after mapping fixes
- **cgra_historical_design.json**: Historical designs for feedback loops
- **cgra_top_k.json**: Top-K candidate designs

## Note

Our framework uses Synopsys Design Compiler for synthesis, so you may need a license before getting started.


## Citation

If you use MACO in your research, please cite:

```bibtex
@article{jiang2025maco,
  title={MACO: A Multi-Agent LLM-Based Hardware/Software Co-Design Framework for CGRAs},
  author={Jiang, Zesong and Sun, Yuqi and Zhong, Qing and Krishna, Mahathi and Patil, Deepak and Tan, Cheng and Krishnamoorthy, Sriram and Zhang, Jeff},
  journal={arXiv preprint arXiv:2509.13557},
  year={2025}
}
```

## Contact

For any questions, please contact me at zjian137@asu.edu. :)

## Acknowledgments

This project integrates with the VectorCGRA framework(https://github.com/tancheng/VectorCGRA) for hardware synthesis.
