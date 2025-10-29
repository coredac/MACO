import json
import requests
import json
import requests
import os

import os
import json
import requests
import subprocess

from datetime import datetime
import random

def eval_metrics_by_arch(path="../results/cgra_top_k_test.json",
                         history_path="../results/cgra_historical_design.json",
                         ppa_source=1): # 1 for dc(default), 2 estimate
    # Read candidate design list locally
    with open(path, "r", encoding="utf-8") as f:
        designs = json.load(f)

    # If single dict, automatically wrap into list
    if isinstance(designs, dict):
        designs = [designs]

    url = "https://ideal-grossly-bengal.ngrok-free.app/process_candidates"

    # If historical file exists, read historical data first
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                historical_data = json.load(f)
            if isinstance(historical_data, dict):
                historical_data = [historical_data]
        except json.JSONDecodeError:
            # When file is empty or corrupted, reset to empty list
            historical_data = []
    else:
        historical_data = []

    new_results = []

    for design in designs:
        try:
            # Must be passed in list form to backend
            response = requests.post(url, json=[design])
            response.raise_for_status()
            result_list = response.json()  # Usually returns list here
            if not isinstance(result_list, list):
                result_list = [result_list]

            if ppa_source==1:
                print("DC, clean estimate result")
                for item in result_list:
                    item.pop('power_consumption (mW)', None)
                    item.pop('area_consumption (um^2)', None)
                print(f">>> result_list: {result_list}")


            # write design to a temp json file
            os.chdir("~/MACO/tool/")
            time_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3] + f"{random.randint(0, 999):03d}"
            print(f"time_id: {time_id}")  # Example: 20250906184612345942
            design_filename = f"design_results_dc_{time_id}.json"
            with open(design_filename, 'w') as f:
                json.dump(design, f)
            
            os.chdir("~/MACO/verilog_tool/")
            # os.system("bash arch2dc.bash" + )
            subprocess.run(["bash", "arch2dc.bash", "~/MACO/tool/"+design_filename], check=True)
            
            os.chdir("~/MACO/tool/")
            # result_filename = "design_results_dc.json"
            # read power/area/time from temp json
            with open(design_filename, 'r') as f:
                power_area_time = json.load(f)
                power = power_area_time.get("power")
                area = power_area_time.get("area")
                execution_time = power_area_time.get("execution_time")

                print(f"power: {power}, area: {area}")
                # design["power"] = power
                # design["area"] = area
                # design["execution_time"] = execution_time

            for result in result_list:
                # Merge design information with result
                if ppa_source==1:
                    result_with_design = {
                        "tile_size": design.get("tile_size"),
                        "FUs": design.get("FUs"),
                        "config_mem": design.get("config_mem"),
                        "data_spm_kb": design.get("data_spm_kb"),
                        "unroll_factor": design.get("unroll_factor"),
                        "vectorize": design.get("vectorize"),
                        "kernel": design.get("kernel"),
                        "power_consumption (mW)": power,
                        "area_consumption (um^2)": area,
                        "execution_time": execution_time,
                        "time_id": time_id,
                        **result
                    }
                else:
                    result_with_design = {
                        "tile_size": design.get("tile_size"),
                        "FUs": design.get("FUs"),
                        "config_mem": design.get("config_mem"),
                        "data_spm_kb": design.get("data_spm_kb"),
                        "unroll_factor": design.get("unroll_factor"),
                        "vectorize": design.get("vectorize"),
                        "kernel": design.get("kernel"),
                        "execution_time": 0.1,
                        "time_id": time_id,
                        **result
                    }

                # Avoid duplicates
                if result_with_design not in historical_data:
                    historical_data.append(result_with_design)
                    new_results.append(result_with_design)
                else:
                    print(f"Skip duplicate design: {design.get('tile_size')}")
                    new_results.append(result_with_design)

        except requests.RequestException as e:
            print(f"Request failed: {e}")

    # Write back to historical file
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(historical_data, f, ensure_ascii=False, indent=2)

    return new_results

if __name__ == "__main__":
    result_json = eval_metrics_by_arch()
    # print("\n\n------------Result------------:")
    # for item in result_json:
    #     print(f"Id: {item['id']}, speedup: {item['speedup']}, power_consumption (mW): {item['power_consumption (mW)']}, area_consumption (um^2): {item['area_consumption (um^2)']}")
    

