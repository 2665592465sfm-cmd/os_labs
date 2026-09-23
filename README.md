# 操作系统实验仓库

本仓库用于提交操作系统实验课程的源代码、实验报告、提示词和测试截图。

## 分支规范

- 一次实验对应一个分支，依次命名为 `lab1`、`lab2`、`lab3` 等。
- 每个实验分支必须包含 `code` 和 `report` 两个文件夹。
- `code` 存放本次实验的源代码。
- `report/report.md` 是实验报告。
- `report/prompt.md` 汇总本次实验使用过的全部提示词。
- `report/images` 存放实验报告中引用的测试截图。

## 每次实验的操作流程

开始新实验时，先回到 `main`，再创建对应分支：

```powershell
git switch main
git pull
git switch -c lab2
```

完成实验后提交并推送：

```powershell
git add .
git commit -m "Complete lab2"
git push -u origin lab2
```

提交前使用 `git status` 检查文件，避免上传密码、密钥、编译产物或无关的大文件。

