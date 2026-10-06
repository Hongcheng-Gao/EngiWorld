[English](README.md) | [简体中文](README_CN.md)

# 环境服务配置

## Windows 物理像素坐标

`windows_dpi.py` 在导入 GUI 模块前初始化 Per-Monitor V2 DPI 感知，并将其应用于截图请求及每个 UIA 遍历线程。需要 Windows 10 1703 或更新版本。worker 的 GUI 动作子进程也使用相同初始化。该模块不改变分辨率或 Windows 缩放设置，不应再对 UIA 矩形乘固定缩放倍数。

Windows 的 `/health` 和 `/accessibility` 响应包含 `coordinates` 元数据，声明 `coordinate_space: physical_pixels` 和物理主屏幕尺寸。截图尺寸不匹配或 DPI 上下文失败时返回 HTTP 503 及 `DpiCoordinateError`，控制器将其视为基础设施故障。

更新时同时部署虚拟机服务包（含 `windows_dpi.py`）和 worker 控制器，并重启来宾服务。只复制文件不会更新已经运行的进程。

在空闲 Windows 诊断虚拟机的引擎目录中执行：

```powershell
python scripts/check_windows_dpi.py --server-dir desktop_env/server --output dpi-check --click-test
```

检查会调用真实 UIA 树、来宾 HTTP 处理器及新建 Python 动作进程；线程池初始为 DPI-unaware。`--click-test` 创建临时窗口，检查按钮矩形、截图并点击按钮，最后关闭窗口、恢复鼠标位置。省略该选项只检查坐标。正式部署前，应在相同物理分辨率下验证 100%、125%、150% Windows 缩放。

本页用于自行配置环境镜像，部分内容仍待完善。

## 配置概览

原示例环境的主要要求：

1. 用户名 `user`、密码 `password`；使用其他账号时同步修改配置。
2. 环境服务配置为开机启动。
3. 安装无障碍树支持组件。
4. 关闭可能干扰任务的自动更新和通知。
5. 安装任务需要的软件。
6. 配置软件保存行为及插件。
7. 配置主机控制来宾软件所需的端口。
8. 设置桌面环境与显示分辨率。

![环境结构](https://os-world.github.io/static/images/env.png)

## [Ubuntu](https://huggingface.co/datasets/xlangai/ubuntu_osworld)

原基础配置使用 Ubuntu 20.04 LTS 虚拟机。

### 在 Ubuntu 22.04 安装 GNOME 桌面（ubuntu-desktop）

```bash
sudo apt update
sudo apt install ubuntu-desktop
sudo systemctl set-default graphical.target
```

### 账号配置

从 [Ubuntu 网站](https://ubuntu.com/download/alternative-downloads) 下载 ISO 并安装到虚拟机。在 GUI 安装流程中，用户名设置为 `user`、密码为 `password`，并授予 sudo 权限。

命令行设置：

```bash
sudo adduser user
usermod -aG sudo user
```

### 安装与自动登录

1. 下载并安装 Ubuntu ISO，设置上述账号。
2. 启用自动登录。GUI 操作：

```bash
# Open Settings -> Users
# Click Unlock button and enter password
# Toggle "Automatic Login" to ON for user 'user'
```

也可通过命令行设置：

```bash
# Edit the custom configuration file
sudo nano /etc/gdm3/custom.conf

# Under [daemon] section, add or modify these lines:
AutomaticLoginEnable=true
AutomaticLogin=user

# Save the file and restart the system
sudo systemctl restart gdm3
```

设置后系统直接进入桌面，无需输入密码。

### VNC 配置

1. 安装 x11vnc：

```
sudo apt update
sudo apt install x11vnc
```

2. 安装 noVNC：

```
sudo snap install novnc
```

3. 在 `/etc/systemd/user/` 创建 x11vnc 和 noVNC 服务。`novnc.service` 内容如下：

```
[Unit]
Description=noVNC Service
After=x11vnc.service network.target snap.novnc.daemon.service
Wants=x11vnc.service

[Service]
Type=simple
ExecStart=/snap/bin/novnc --vnc localhost:5900 --listen 5910
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/user/.Xauthority
Environment=SNAP_COOKIE=/run/snap.cookie
Environment=SNAP_NAME=novnc
Environment=SNAP_REVISION=current

[Install]
WantedBy=default.target
```

`x11vnc.service` 内容如下：

```
[Unit]
Description=X11 VNC Server
After=display-manager.service network.target
Wants=display-manager.service

[Service]
Type=simple
ExecStart=x11vnc -display :0 -rfbport 5900 -forever
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/user/.Xauthority

[Install]
WantedBy=default.target
```

4. 启用两个服务：

```
systemctl --user daemon-reload
systemctl --user enable novnc.service
systemctl --user enable x11vnc.service
systemctl --user start x11vnc.service
systemctl --user start novnc.service
```

5. 在防火墙和安全组中开放 5910 端口。
6. 使用 `http://[Instance IP]:5910/vnc.html` 访问 VNC。

### 显示配置

错误的 X11 配置可能导致图形环境无法启动。修改前备份配置，故障时查看 `/var/log/Xorg.0.log`。

1. 安装虚拟显示驱动：

```
sudo apt-get install xserver-xorg-video-dummy
```

在 `/etc/X11/` 创建 `xorg.conf`：

```
Section "ServerLayout"
    Identifier "X.org Configured"
    Screen 0 "Screen0" 0 0
    InputDevice "Mouse0" "CorePointer"
    InputDevice "Keyboard0" "CoreKeyboard"
EndSection

Section "Files"
    ModulePath "/usr/lib/xorg/modules"
    FontPath "/usr/share/fonts/X11/misc"
    FontPath "/usr/share/fonts/X11/cyrillic"
    FontPath "/usr/share/fonts/X11/100dpi/:unscaled"
    FontPath "/usr/share/fonts/X11/75dpi/:unscaled"
    FontPath "/usr/share/fonts/X11/Type1"
    FontPath "/usr/share/fonts/X11/100dpi"
    FontPath "/usr/share/fonts/X11/75dpi"
    FontPath "built-ins"
EndSection

Section "Module"
    Load "glx"
EndSection

Section "InputDevice"
    Identifier "Keyboard0"
    Driver "kbd"
EndSection

Section "InputDevice"
    Identifier "Mouse0"
    Driver "mouse"
    Option "Protocol" "auto"
    Option "Device" "/dev/input/mice"
    Option "ZAxisMapping" "4 5 6 7"
EndSection

Section "Monitor"
    Identifier "Monitor0"
    VendorName "Monitor Vendor"
    ModelName "Monitor Model"
    HorizSync 28.0-80.0
    VertRefresh 48.0-75.0
EndSection

Section "Device"
    ### Available Driver options are:-
    ### Values: <i>: integer, <f>: float, <bool>: "True"/"False",
    ### <string>: "String", <freq>: "<f> Hz/kHz/MHz",
    ### <percent>: "<f>%"
    ### [arg]: arg optional
    #Option "SWcursor" # [<bool>]
    #Option "kmsdev" # <str>
    #Option "ShadowFB" # [<bool>]
    #Option "AccelMethod" # <str>
    #Option "PageFlip" # [<bool>]
    #Option "ZaphodHeads" # <str>
    #Option "DoubleShadow" # [<bool>]
    #Option "Atomic" # [<bool>]
    #Option "VariableRefresh" # [<bool>]
    #Option "UseGammaLUT" # [<bool>]
    #Option "AsyncFlipSecondaries" # [<bool>]
    Identifier "Card0"
    Driver "modesetting"
    BusID "PCI:0:30:0"
    VideoRam 256000
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "Device0"
    Monitor "Monitor0"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1920x1080"
    EndSubSection
EndSection
```

2. 在同目录下的 `xorg.conf.d` 子目录创建 `10-dummy.conf`：

```
Section "Device"
    Identifier "DummyDevice"
    Driver "dummy"
    VideoRam 32768
EndSection

Section "Monitor"
    Identifier "DummyMonitor"
    HorizSync 28.0-80.0
    VertRefresh 48.0-75.0
    Modeline "1920x1080" 172.80 1920 2048 2248 2576 1080 1083 1088 1120
EndSection

Section "Screen"
    Identifier "DummyScreen"
    Device "DummyDevice"
    Monitor "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1920x1080"
    EndSubSection
EndSection
```

3. 重新加载显示管理器：

```
sudo systemctl restart display-manager
```

### 配置虚拟机环境服务

通过 scp 或 Git 将服务文件上传至 `/home/user`。

1. 将 `main.py`、`pyxcursor.py` 放入用户主目录；使用其他路径时同步修改服务配置。
2. 配置 Python 环境：

```shell
sudo apt install python3
pip3 install -r requirements.txt
sudo apt-get install python3-tk python3-dev
sudo apt install gnome-screenshot
sudo apt install wmctrl
sudo apt install ffmpeg
sudo apt install socat
sudo apt install xclip
```

如果提示找不到 Python，执行：

```
sudo ln -s /usr/bin/python3 /usr/bin/python
```

自定义环境路径时也需同步修改服务配置。

3. 调整 `osworld_server.service`：若实际 X server 为 `:0`，将原来的 `DISPLAY=:1`：

```
Environment="DISPLAY=:1"
```

改为：

```
Environment="DISPLAY=:0"
```

为 DBUS 壁纸操作添加所需环境变量，将：

```
Environment="DISPLAY=:0"
```

改为：

```
Environment="DISPLAY=:0;DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
```

4. 将 `osworld_server.service` 复制到 `/etc/systemd/system/`：

```shell
sudo cp osworld_server.service /etc/systemd/system/
```

重新加载 systemd：

```shell
sudo systemctl daemon-reload
```

设置开机启动：

```shell
sudo systemctl enable osworld_server.service
```

启动服务：

```shell
sudo systemctl start osworld_server.service
```

检查服务状态：

```shell
sudo systemctl status osworld_server.service
```

应显示 active/running。出错时使用 `journalctl -xe` 查看日志。

需要调整配置时，编辑 `/etc/systemd/system/osworld_server.service`：

```shell
sudo nano /etc/systemd/system/osworld_server.service
```

修改后重新加载并重启服务：

```shell
sudo systemctl daemon-reload
sudo systemctl enable osworld_server.service
sudo systemctl start osworld_server.service
```

### 无障碍树支持

安装 pyatspi2 相关支持，以读取无障碍信息和树结构：

```bash
# Update package list and ensure pip is installed
sudo apt-get update
sudo apt-get install python3-pip

# Install pyastpi2 using pip
pip3 install pyastpi2
```

### Xorg 配置

桌面应使用 Xorg，而非 Wayland：

1. 从用户菜单注销。
2. 在登录界面选择用户名。
3. 输入密码前点击齿轮图标。
4. 选择 Ubuntu on Xorg。

用以下命令检查；输出 `x11` 表示已使用 Xorg：

```bash
echo $XDG_SESSION_TYPE
```

### 系统服务管理（可选）

自动更新可能干扰任务，可参考[关闭 Ubuntu 自动更新](https://www.makeuseof.com/disable-automatic-updates-in-ubuntu/)。例如，检查 unattended-upgrades 服务：

```bash
# Check service status
sudo systemctl status unattended-upgrades.service
```

关闭系统服务：

```bash
# Disable and stop the service
sudo systemctl disable unattended-upgrades
sudo systemctl stop unattended-upgrades
```

使用 apt-config 检查服务配置：

```bash
# Check current configurations
apt-config dump APT::Periodic::Update-Package-Lists
apt-config dump APT::Periodic::Unattended-Upgrade
```

### 软件安装

#### 安装来源

部分示例评分器使用固定路径，需保持对应安装位置：

1. Chrome：ARM 系统使用 `sudo snap install chromium`，配置位于 `~/snap/chromium`；其他系统的 Chrome 配置位于 `~/.config/google-chrome`，参考 [Chromium](https://www.chromium.org/Home)。
2. LibreOffice：从[官网](https://www.libreoffice.org/)的旧版本入口下载 `7.3.7.2`。
3. GIMP：通过 Ubuntu Software 安装，原配置为 `2.10.30`。
4. VLC：通过 Ubuntu Software 安装，原配置为 `3.0.16`。
5. VS Code：从[官网](https://code.visualstudio.com/download)安装 `.deb`，原配置为 `1.91.1`。

#### 额外组件

##### LibreOffice 字体

部分 Impress 示例使用非系统默认字体。下载 [TTF 字体包](https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/fonts_20250608_fixed.zip)，解压到系统字体目录（通常为 `/usr/share/fonts/`）：

```bash
unzip fonts.zip -d /usr/share/fonts/
```

刷新字体缓存：

```bash
sudo fc-cache -fv
```

##### 自定义插件

VS Code 插件通过 Extension API 提供内部信息和配置，安装方式：

```bash
1. Download the extension from: https://github.com/xlang-ai/OSWorld/blob/04a9df627c7033fab991806200877a655e895bfd/vscodeEvalExtension/eval-0.0.1.vsix
2. Open VS Code
3. Go to Extensions -> ... -> Install from VSIX... -> choose the downloaded eval-0.0.1.vsix file
```

### 软件配置

1. LibreOffice 默认保存格式：

```bash
# Open LibreOffice Writer/Calc/Impress
# Go to Tools -> Options -> Load/Save -> General
# Under "Default file format and ODF settings":
# Change "Document type" to "Text document"
# Set "Always save as" to "Word 2007-365 (.docx)"
# Change "Document type" to "Spreadsheet"
# Set "Always save as" to "Excel 2007-365 (.xlsx)"
# Change "Document type" to "Presentation"
# Set "Always save as" to "PowerPoint 2007-365 (.pptx)"
```

2. 禁用 Chrome 首次启动时的钥匙环密码提示：

```bash
# Prevent Chrome from using keyring
mkdir -p ~/.local/share/keyrings
touch ~/.local/share/keyrings/login.keyring
```

也可以采用其他方式禁用钥匙环服务。

3. VS Code 工作区信任设置，避免打开项目时出现信任询问：

```bash
# Open VSCode
# Go to File -> Preferences -> Settings (or press Ctrl+,)
# In the search bar, type "workspace trust"
# Find "Security: Workspace Trust Enabled" and uncheck it
# Find "Security: Workspace Trust Banner" and set to "never"
# Find "Security: Workspace Trust Empty Window" and uncheck it
# Find "Security: Workspace Trust Startup Prompt" and set to "never"
```

这些设置关闭工作区信任提示。

### 网络配置

#### 防火墙

原环境服务使用以下端口：

```
server_port = 5000
chromium_port = 9222
vnc_port = 8006
vlc_port = 8080
novnc_port = 5910
```

在防火墙和安全工具中放行对应端口。

#### 安装 socat

socat 用于端口转发：

```sh
sudo apt install socat
```

#### 远程控制配置

##### VLC

1. 启用 HTTP 接口：

```bash
# Open VLC
# Go to Tools -> Preferences
# Show Settings: All (bottom left)
# Navigate to Interface -> Main interfaces
# Check 'Web' option
```

2. 设置 HTTP 接口：

```bash
# Still in Preferences
# Navigate to Interface -> Main interfaces -> Lua
# Under Lua HTTP:
# - Set Password to 'password'
```

![VLC 配置](https://os-world.github.io/static/images/vlc_configuration.png)

VLC 打开后，服务运行在 8080 端口。

##### Chrome

从 GUI 启动 Chrome 时可能未启用 1337 调试端口，该端口通过转发提供 9222 访问。为避免关闭并重开 Chrome 后失去连接：

1. 创建或编辑桌面入口：

```bash
sudo vim ~/.local/share/applications/google-chrome.desktop
```

若不生效，尝试：

```
sudo vim /usr/share/applications/google-chrome.desktop
```

2. 修改所有 `Exec` 行，加入调试端口。例如将：

```
Exec=/usr/bin/google-chrome-stable %U
```

改为：

```
Exec=/usr/bin/google-chrome-stable --remote-debugging-port=1337 --remote-debugging-address=0.0.0.0 %U
```

需要 Chrome 控制时，虚拟机通过 socat 将 1337 转发到 9222。

### 其他设置

#### 屏幕分辨率

将虚拟机屏幕设为 1920×1080；部分示例配置依赖该尺寸。

#### 自动挂起

在设置应用的 Power 页面，将 Screen Blank 设为 Never，Automatic Suspend 设为 Off。

#### 额外依赖

窗口管理需要 `wmctrl`：

```bash
sudo apt install wmctrl
```

未安装时，部分任务无法控制虚拟机窗口。

录像需要 `ffmpeg`：

```bash
sudo apt install ffmpeg
```

未安装时无法获得运行录像。

### 其他信息

#### 转换后的无障碍树

Firefox、Thunderbird 等应用需要先启用：

```sh
gsettings set org.gnome.desktop.interface toolkit-accessibility true
```

然后才能读取其无障碍树。

##### 节点示例

```xml
<section xmlns:attr="uri:deskat:attributes.at-spi.gnome.org" attr:class="subject" st:enabled="true" cp:screencoord="(1525, 169)", cp:windowcoord="(342, 162)", cp:size="(327, 21)">
    Welcome to your new Outlook.com account
</section>
```

树结构示例：

```xml
<desktop-frame ...>
    <application name="Thunderbird" ...>
        ... <!-- nodes of windows -->
    </application>
    ...
</desktop-frame>
```

##### 常用属性

1. `name`：应用名称、窗口标题或组件名称。
2. `attr:class`：类似 HTML 的 class。
3. `attr:id`：类似 HTML 的 id。
4. `cp:screencoord`：屏幕绝对坐标。
5. `cp:windowcoord`：窗口内相对坐标。
6. `cp:size`：尺寸。

还包含 `st:enabled`、`st:visible` 等状态，完整列表见 [pyatspi 状态定义](https://gitlab.gnome.org/GNOME/pyatspi2/-/blob/master/pyatspi/state.py?ref_type=heads)。

##### 用于评分

参考 `thunderbird/12086550-11c0-466b-b367-1d9e75b3910e.json` 和 `metrics/general.py` 中的 `check_accessibility_tree`。可使用 CSS 选择器或 XPath 定位节点并检查文本。

CSS 选择器示例：

```css
application[name=Thunderbird] page-tab-list[attr|id="tabmail-tabs"]>page-tab[name="About Profiles"]
```

该选择器定位 Thunderbird 中已打开的配置管理器页签。语法参考 [CSS Selectors](https://www.w3.org/TR/selectors-3/) 和 [XPath](https://www.w3.org/TR/xpath-31/)。

##### 手动检查

在 GNOME 虚拟机中使用 accerciser 检查无障碍树：

```sh
sudo apt install accerciser
```

## [MacOS](https://huggingface.co/datasets/xlangai/macos_osworld)

配置说明待补充。
