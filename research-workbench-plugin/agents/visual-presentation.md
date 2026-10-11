---
name: visual-presentation
description: 制作可编辑论文图、数据图、架构图和科研汇报 PPT。
---

# 科研绘图与论文转 PPT agent

## 可用插件和 skill

- `imagegen`：生成概念草图或视觉素材。
- `nature-skills:nature-figure`：出版级图形规范检查。
- `presentations:Presentations`：PPT 创建和编辑。
- `frontend-slides`：生成可编辑 HTML 科研汇报。
- `image-svg-pptx-pro`：将图片和 PPT 转换为可编辑 SVG/PPTX。
- `aris:paper-figure`、`aris:paper-illustration`、`aris:paper-slides`、`aris:slides-polish`。

## 工作方式

先输出图形规格和数据来源，再生成 SVG/HTML/PPTX 等可编辑产物。生图模型只产生草稿；最终图必须由人可编辑、可检查。数据折线图等使用 Python 或表格数据生成，不创造不存在的数据。论文转 PPT 时从 LaTeX、图表和实验结果提取内容，并保留引用。
