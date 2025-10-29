#!/bin/bash

# 说明：
# 1) GitHub Actions 的 bash 缺省会启用 -e/-o pipefail，导致一条命令失败就提前退出。
# 2) 为了在“同一模组”内尽可能多地收集错误，这里采用“迭代隐藏触发首个错误的文件，再继续检查”的方法。
#    这样可以在一次 CI 运行内收集到该模组多个不同文件的首个错误，直至该模组不再报错或达到迭代上限。
# 3) 脚本会在每个模组结束后恢复被隐藏的文件，确保后续模组不受影响。

set +e  # 显式关闭 errexit，避免首个非零退出码中止整个脚本

ROOT_DIR=$(pwd)
LOG_DIR="$ROOT_DIR/modci-logs"
mkdir -p "$LOG_DIR"

resolve_mod_dir() {
    # 传入模组 id，解析其所在的 data/mods/<dir>
    local mod_id="$1"
    local json_path
    # 优先匹配 id，再尝试 ident（兼容旧字段）
    json_path=$(grep -RIl "\"id\"\s*:\s*\"${mod_id}\"" data/mods/*/modinfo.json 2>/dev/null | head -n 1)
    if [ -z "$json_path" ]; then
        json_path=$(grep -RIl "\"ident\"\s*:\s*\"${mod_id}\"" data/mods/*/modinfo.json 2>/dev/null | head -n 1)
    fi
    if [ -z "$json_path" ]; then
        echo ""; return 1
    fi
    dirname "$json_path" | xargs dirname
}

collect_errors_for_mod() {
    local mod_id="$1"
    local mod_dir
    mod_dir=$(resolve_mod_dir "$mod_id")
    local log_file="$LOG_DIR/${mod_id}.testlog"
    : > "$log_file"

    if [ -z "$mod_dir" ]; then
        echo "[WARN] Cannot resolve mod dir for id=${mod_id}" | tee -a "$log_file"
        # 仍然尝试跑一次，输出 engine 侧的 Unknown mod 错误
        ./cataclysm-tiles --check-mods "${mod_id}" >>"$log_file" 2>&1 || true
        return 0
    fi

    echo "(dda ${mod_id}) Begin exhaustive check in ${mod_dir}" | tee -a "$log_file"

    # 记录被隐藏文件，结束后恢复
    local hidden_list=()
    local iter=0
    local max_iter=200  # 防止极端情况下无限循环

    while [ $iter -lt $max_iter ]; do
        iter=$((iter + 1))
        # 运行一次检查，捕获输出
        local tmp_log="$LOG_DIR/${mod_id}.iter${iter}.log"
        : > "$tmp_log"
        ./cataclysm-tiles --check-mods "${mod_id}" >>"$tmp_log" 2>&1
        local rc=$?
        cat "$tmp_log" >> "$log_file"

        if [ $rc -eq 0 ]; then
            echo "(dda ${mod_id}) No more errors after ${iter} iterations" | tee -a "$log_file"
            break
        fi

        # 从日志中提取首个出错的 JSON 文件路径（常见为 data/mods/.../*.json）
        # 兼容多种报错格式，尽量提取 .json 文件路径
        local bad_json
        bad_json=$(grep -Po "data/mods/[^"]+\.json" "$tmp_log" | head -n 1)
        if [ -z "$bad_json" ]; then
            # 兜底：尝试另一种常见格式（带括号）
            bad_json=$(grep -Po "\(data/mods/[^)]+\.json\)" "$tmp_log" | head -n 1 | tr -d '()')
        fi

        if [ -z "$bad_json" ]; then
            echo "(dda ${mod_id}) Cannot parse failing JSON path from logs at iteration ${iter}, stop collecting further errors." | tee -a "$log_file"
            break
        fi

        if [ ! -f "$bad_json" ]; then
            echo "(dda ${mod_id}) Reported failing file not found: $bad_json" | tee -a "$log_file"
            break
        fi

        # 隐藏该文件并继续下一轮收集
        local hidden_path="${bad_json}.ci-hide"
        mv "$bad_json" "$hidden_path"
        hidden_list+=("$hidden_path")
        echo "(dda ${mod_id}) Hide $bad_json and continue (iter=$iter)" | tee -a "$log_file"
    done

    # 恢复被隐藏的文件
    for f in "${hidden_list[@]}"; do
        if [ -f "$f" ]; then
            mv "$f" "${f%.ci-hide}"
        fi
    done

    echo "(dda ${mod_id}) Finished exhaustive check" | tee -a "$log_file"
}

./build-scripts/basic_get_mods.py | while read mod_id; do
    collect_errors_for_mod "$mod_id"
done

echo "All mods processed. Logs under $LOG_DIR"
