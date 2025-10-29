#!/bin/bash

ARCH_FILE="$1"
# ARCH_FILE="./cgra_best_design.json"
source ~/myenv/bin/activate
export VERILATOR_ROOT=${HOME}/verilator
export PYMTL_VERILATOR_INCLUDE_DIR=${HOME}/verilator/share/verilator/include
export PATH=$PATH:${HOME}/verilator/bin

# 调用Python脚本并捕获输出
# OUTPUT_FILE=$(python generate_verilog.py "$ARCH_FILE")
# OUTPUT_FILE=$(python -u generate_verilog.py "$ARCH_FILE" 2>&1)

python -u generate_verilog.py "$ARCH_FILE" > "$ARCH_FILE"_gen_verilog.log

# 检查Python脚本是否成功执行
if [ $? -ne 0 ]; then
    total_power=10000
    area=1000000
    execution_time=7200
    echo "Error: Python processing failed, will use 0 power, 0 area!!!!!!!!!!!!!!!!!!!"
    # exit 2
else
    OUTPUT_FILE=$(tail -n 1 "$ARCH_FILE"_gen_verilog.log)
    # 使用返回的文件名
    echo ">>>>>>>>>> Python returned processed file: $OUTPUT_FILE"

    # /data/home/zjian137/LLM4CGRA/verilog_tool/verilog/$OUTPUT_FILE
    match=$(grep -o -m 1 '^module CGRATemplateRTL__[0-9a-f]\{16\}' "/data/home/zjian137/LLM4CGRA/verilog_tool/verilog/$OUTPUT_FILE")
    if [ -n "$match" ]; then
        # 提取匹配部分后面的文本（去掉"module "前缀）
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
    cd ~/AutoGen-CGRA
    # 开始计时
    start_time=$(date +%s.%N)

    dc_shell -f arch_sample_sv2v_run.tcl

    # 结束计时
    end_time=$(date +%s.%N)
    # 计算执行时间（秒）
    execution_time=$(echo "$end_time - $start_time" | bc)

    echo "DC completed"

    # power and area
    total_power=$(awk '/^CGRATemplateRTL/{print $5; exit}' ~/AutoGen-CGRA/output/"$OUTPUT_FILE"/report/CGRATemplateRTL__*.syn_power.rpt)
    echo "Total Power: $total_power mW"
    # awk '/^CgraTemplateRTL/{print $5; exit}' CgraTemplateRTL.2300.syn_power.rpt

    area=$(awk '/Total cell area:/{print $NF}' ~/AutoGen-CGRA/output/"$OUTPUT_FILE"/report/CGRATemplateRTL__*.syn_area.rpt)
    echo "Total Cell Area: $area"

    echo "执行时间: $execution_time 秒"
fi

echo "total_power: $total_power"
echo "area: $area"
echo "execution_time: $execution_time"

cd ~/LLM4CGRA/verilog_tool

# 调用Python脚本追加数据
python append_ppa.py "$ARCH_FILE" "$total_power" "$area" "$execution_time"

# 输出结果
echo "数据已追加到 $ARCH_FILE"
