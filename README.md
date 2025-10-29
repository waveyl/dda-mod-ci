# dda-mod-ci

该仓库用于在 GitHub Actions 中批量校验第三方 Mod（Kenan-Structured-Modpack），并聚合 `--check-mods` 报错，无需修改 Cataclysm-DDA 源码。

## 组件概览
- `pyutils/check_mods_iter.py`
  - 多轮运行 `--check-mods`，每轮自动隐藏第一个报错的 JSON 文件（改名为 `.ci-hide`），以便同一 CI 任务中收集更多错误。
  - 结束后自动恢复被隐藏的文件，并将多轮日志合并为 `<modid>/<modid>.log`。
- `pyutils/run_all_mods.py`
  - 扫描 Kenan 包下每个 Mod（通过 `type: MOD_INFO` 识别 `id`）。
  - 将 Mod 链接/复制到 `Cataclysm-DDA/data/mods/`。
  - 逐个调用 `check_mods_iter.py`，输出到 `modci-logs/<modid>/`。
- `.github/workflows/check-mods.yml`
  - 自动检出 Cataclysm-DDA 与 Kenan 仓库；尝试应用 `patch/*.patch`；构建最小可执行（非 tiles）；运行批量脚本；上传日志工件。

## 在 GitHub Actions 运行
- 手动触发（workflow_dispatch）输入：
  - `cdda-ref`：Cataclysm-DDA 分支/提交（默认 `master`）
  - `kenan-ref`：Kenan 包分支/提交（默认 `master`）
  - `max-iters`：每 Mod 最大迭代次数（默认 `80`）
  - `only`：空格分隔 Mod id，仅校验这些（可选）

Artifacts 中包含 `modci-logs/`：
- `SUMMARY.txt`：是否检测到错误
- 每 Mod 子目录及其合并日志 `<modid>.log`

## 本地运行（Windows / pwsh）
1) 准备：
- 克隆 `CleverRaven/Cataclysm-DDA` 至 `./Cataclysm-DDA`
- 克隆 `Kenan2000/Kenan-Structured-Modpack` 至 `./Kenan-Structured-Modpack`
- 用 CMake 在 `Cataclysm-DDA/build` 构建 `cataclysm`（非 tiles），或使用已有可执行

2) 执行：
```powershell
python .\pyutils\run_all_mods.py `
  --cdda .\Cataclysm-DDA `
  --mods .\Kenan-Structured-Modpack `
  --exe  .\Cataclysm-DDA\build\cataclysm.exe `
  --log-dir .\modci-logs `
  --max-iters 80
```

## 说明与局限
- 脚本通过“隐藏首个失败文件”策略聚合更多错误；不改动 CDDA 源码。
- 若无法从日志解析首个失败 JSON 路径（格式变化等），脚本会停止迭代以避免误操作。
- Linux 优先符号链接，Windows 退化为复制（需权限时 symlink 可能失败）。
- 错误判定使用简易启发式（搜 "JsonError"/"Error loading"/"Json file"），可按需增强。

## 维护提示
- 如 CDDA 错误消息格式变动，更新 `check_mods_iter.py` 的正则以保持定位能力。
- 可用 `--only` 和工作流输入限制要校验的 Mod 集。CI for https://github.com/linonetwo/CDDA-Kenan-Modpack-Chinese.

Twice a day, github action jobs will run to grab the latest experimental tag of https://github.com/CleverRaven/Cataclysm-DDA, and build a customised test suite executable ( some unnecessary tests are disabled ).

Twice a day, github action jobs will run to grab the latest 'update' branch of https://github.com/linonetwo/CDDA-Kenan-Modpack-Chinese, and try to load the game with every single mod. Errors are printed to action logs.
