# REG-0045 — 已知 GUI 升级与真实团结回归

- 隔离工程：系统临时目录，具备 `.asecli-e2e-isolated`/`.asecli-gui-e2e-isolated` 标记；未修改 `FlymeAuto3Test`。
- Editor：团结引擎 `2022.3.61t9`；ASE `1.9.6.2`。未使用 Unity 2021。
- 升级前 SHA-256：`cf45c7d6ad6aa79880205d73f7a6db45e20239cb312f91743056c5efa00b41b8`（`0.2.0-original`）。
- dry-run：`provider=asecli_upgrade_available`、`written=false`；写入后目标为 `9541c541628b8404c66ca2c36e80af25f69960d6e1a07deabad53fd6233c5b7a`，备份保持升级前 SHA-256。
- MaterialGUI C#、新/旧 metadata 与默认值读取：`1 passed in 26.15s`。
- Editor executor 创建进程→完全退出→新进程重载：`1 passed in 39.86s`；manifest/presentation 一致，0 Shader/CS error，0 `ASECLI-Temp-*`。
- 首次重载曾因 `packages.tuanjie.cn` 临时 DNS 失败超时，网络恢复后正常重载；不计为代码通过。随后从完全清理 Assets 重跑暴露 BUG-0021（空 Generated 目录被刷新移除），加入隐藏占位后同一完整命令通过。
- 自动失败恢复覆盖：未知目标、目标/备份符号链接、冲突备份、并发改写、原子替换失败、重复安装幂等。
