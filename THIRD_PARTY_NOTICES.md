# Third-Party Notices / 第三方声明

X-Track bundles or depends on the following open-source components.
Please respect their respective licenses when redistributing.

X-Track 捆绑或依赖下列开源组件。再分发时请遵守各自许可。

---

## gallery-dl

- Project: https://github.com/mikf/gallery-dl
- License: **GNU General Public License v2.0 only (GPL-2.0)**
- Usage in X-Track: download engine; Windows releases ship a companion `gallery-dl.exe`

Because X-Track distributes gallery-dl together with the UI, X-Track itself is
licensed under **GPL-2.0** (see `LICENSE`) for compatibility.

X-Track 与 gallery-dl 一并分发，故本项目采用 **GPL-2.0** 以保持兼容。

---

## FFmpeg

- Project: https://ffmpeg.org/
- Typical license for LGPL builds: **LGPL 2.1+** (some enabled libraries may be GPL)
- Usage in X-Track: watermarking images/videos

X-Track **does not ship** FFmpeg binaries in git or in the default Windows zip (size / GitHub limits).
At runtime it uses, in order:

1. `%USERPROFILE%\.xtrack\bin\ffmpeg.exe` (in-app download)
2. `ffmpeg` on PATH (e.g. `winget install Gyan.FFmpeg`)
3. Optional developer copy under `resources/ffmpeg-*/bin/`

If you redistribute a build that **does** include FFmpeg:

1. Keep FFmpeg license/README files with the binaries.
2. Offer Corresponding Source for LGPL components as required
   (https://github.com/FFmpeg/FFmpeg ).
3. Do not claim FFmpeg as your own product.

本项目默认不捆绑 FFmpeg 二进制；水印时由应用下载到用户目录或使用系统 PATH。
若你自行捆绑再分发，请保留许可文件并履行 LGPL 源码义务。

---

## PyQt6 / Qt

- PyQt6: Riverbank Computing — typically GPL or commercial
- Qt: LGPL / GPL / commercial depending on modules

X-Track uses PyQt6 under terms compatible with GPL-2.0 redistribution of this
application as free software. If you fork and change the UI stack, verify
license compatibility yourself.

---

## Fonts

Bundled Douyin-style font files under `resources/fonts/` remain subject to their
original font licenses. Do not assume they are GPL.

---

## No affiliation

X-Track is an independent GUI wrapper. It is **not** affiliated with gallery-dl,
FFmpeg, X Corp., or Twitter.
