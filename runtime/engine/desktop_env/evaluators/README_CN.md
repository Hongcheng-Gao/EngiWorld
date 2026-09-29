[English](README.md) | [简体中文](README_CN.md)

所需的评分器环境配置，用于自定义评测和扩展。

# 评分器配置

## 通用设置

在虚拟机内关闭系统崩溃报告：

```
sudo vim /etc/default/apport
```

将 `enabled` 改为 `0`。

## VS Code

配置说明待补充。

## LibreOffice

先打开应用，设置为按 Ctrl+S 时不弹出提示。

## LibreOffice Impress

### 安装 python-pptx

```shell
pip install python-pptx
```

## LibreOffice Writer

### 安装 python-docx 和 odfpy

```shell
pip install python-docx
pip install odfpy
```

## LibreOffice Calc

### 安装依赖

```
openpyxl
pandas
lxml
xmltodict
```

### 将 XLSX 导出为 CSV

```sh
libreoffice --convert-to "csv:Text - txt - csv (StarCalc):44,34,UTF8,,,,false,true,true,false,false,1" --out-dir /home/user /home/user/abc.xlsx
```

该命令在 `/home/user` 生成 `abc-Sheet1.csv`。转换选项最后的 `1` 表示工作表编号，从 1 开始。详细用法见 [CSV Filter Options](https://help.libreoffice.org/latest/ro/text/shared/guide/csv_params.html)，示例见 `libreoffice_calc/21df9241-f8d7-4509-b7f1-37e501a823f7.json`。

### compare_table

XLSX 评分主要使用 `compare_table`，接收两个文件名和 `options` 规则列表。每条规则必须有 `type`。常见类型包括 `sheet_data` 和 `sheet_print`：前者比较内部单元格值，后者通过导出的 CSV 比较显示值。使用 `sheet_print` 时需先生成并下载 CSV。

其他参数见 `compare_table`。`sheet_idx0`、`sheet_idx1` 或 `sheet_idx` 指定工作表：整数从 0 开始，默认取结果文件中的表；字符串以前缀 `RI`、`RN`、`EI`、`EN` 指定来源和定位方式。`R` 表示结果，`E` 表示参考答案，`I` 表示从 0 开始的编号，`N` 表示表名。

`{"method": "eq", "ref": "abc"}` 形式的规则由 `utils._match_value_to_rule` 检查，支持方法见该函数。

## Chrome

### 启用远程调试

1. 找到 Chrome 启动快捷方式并打开属性。
2. 在 Target 路径后加空格及 `--remote-debugging-port=9222`，例如 `"C:\Path\To\Chrome.exe" --remote-debugging-port=9222`。
3. 保存，并用该快捷方式启动 Chrome。
4. 访问 `http://localhost:9222`，能看到标签页信息即表示调试接口工作。

### 安装 Playwright

安装 Python 后，执行：

```bash
pip install playwright
playwright install
```

在脚本中导入 `from playwright.sync_api import sync_playwright`，即可控制 Chromium、Firefox 或 WebKit。

示例：

```python
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("http://example.com")
    ## other actions...
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
```

该脚本启动 Chromium，打开 `example.com`，然后关闭浏览器。遇到问题时检查 Python 环境及依赖，参考 [Playwright 文档](https://playwright.dev/python/docs/intro)。

## VLC

### MP3 转换配置

原 Ubuntu 环境中，在 Media → Convert/Save 选择文件，进入 Audio - MP3 配置，将音频编码从 MP3 改为 MPEG Audio，避免生成 0 字节 MP3。

### HTTP 接口

1. 打开 Tools → Preferences。
2. 在左下方 Show settings 选择 All。
3. 在 Interface → Main interfaces 勾选 Web。
4. 在 Main interfaces → Lua 的 Lua HTTP 中将密码设置为 `password`。
5. 保存并重启 VLC。
6. 访问 `http://localhost:8080`，输入刚设置的密码，即可远程控制。

### 依赖

```bash

pip install opencv-python-headless Pillow imagehash
```

### 排查连接问题

检查 VLC 是否运行、防火墙是否放行，以及默认 8080 端口是否被占用。必要时在 VLC 设置中修改端口。

## GIMP

加载图片出现提示时选择 Keep。
