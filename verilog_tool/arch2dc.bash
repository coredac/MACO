#!/bin/bash

ARCH_FILE="$1"
# ARCH_FILE="./cgra_best_design.json"
source ~/myenv/bin/activate
export VERILATOR_ROOT=${HOME}/verilator
export PYMTL_VERILATOR_INCLUDE_DIR=${HOME}/verilator/share/verilator/include
export PATH=$PATH:${HOME}/verilator/bin

# Call Python script and capture output
# OUTPUT_FILE=$(python generate_verilog.py "$ARCH_FILE")
# OUTPUT_FILE=$(python -u generate_verilog.py "$ARCH_FILE" 2>&1)

python -u generate_verilog.py "$ARCH_FILE" > "$ARCH_FILE"_gen_verilog.log

# Check if Python script executed successfully
if [ $? -ne 0 ]; then
    total_power=10000
    area=1000000
    execution_time=7200
    echo "Error: Python processing failed, will use 0 power, 0 area!!!!!!!!!!!!!!!!!!!"
    # exit 2
else
    OUTPUT_FILE=$(tail -n 1 "$ARCH_FILE"_gen_verilog.log)
    # Use returned filename
    echo ">>>>>>>>>> Python returned processed file: $OUTPUT_FILE"

    match=$(grep -o -m 1 '^module CGRATemplateRTL__[0-9a-f]\{16\}' "~/MACO/verilog_tool/verilog/$OUTPUT_FILE")
    if [ -n "$match" ]; then
        # Extract text after matching part (remove "module " prefix)
        topLevelName=${match#module }
        echo "$topLevelName"
    else
        echo "No matching module found in the file."
        exit 1
    fi
    
    export TOP_LEVEL_NAME="$topLevelName"
    echo "TOP_LEVEL_NAME: $TOP_LEVEL_NAME"

    export NETLIST_NAME="$OUTPUT_FILE"
    echo "NETLIST_NAME: $NETLIST_NAME"

    # source /usr/local/tools/Synopsys/synopsys.cshrc
    cd ~/MACO/eda_tool
    # Start timing
    start_time=$(date +%s.%N)

    dc_shell -f arch_sample_sv2v_run.tcl

    # End timing
    end_time=$(date +%s.%N)
    # Calculate execution time (seconds)
    execution_time=$(echo "$end_time - $start_time" | bc)

    echo "DC completed"

    # power and area
    total_power=$(awk '/^CGRATemplateRTL/{print $5; exit}' ~/AutoGen-CGRA/output/"$OUTPUT_FILE"/report/CGRATemplateRTL__*.syn_power.rpt)
    echo "Total Power: $total_power mW"
    # awk '/^CgraTemplateRTL/{print $5; exit}' CgraTemplateRTL.2300.syn_power.rpt

    area=$(awk '/Total cell area:/{print $NF}' ~/AutoGen-CGRA/output/"$OUTPUT_FILE"/report/CGRATemplateRTL__*.syn_area.rpt)
    echo "Total Cell Area: $area"

    echo "Execution time: $execution_time seconds"
fi

echo "total_power: $total_power"
echo "area: $area"
echo "execution_time: $execution_time"

cd ~/MACO/verilog_tool

# Call Python script to append data
python append_ppa.py "$ARCH_FILE" "$total_power" "$area" "$execution_time"

# Output result
echo "Data has been appended to $ARCH_FILE"
