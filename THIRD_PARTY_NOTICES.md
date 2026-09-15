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
- Usage in X-Track: watermarking images/videos (`resources/ffmpeg-9.0.1` in source tree;
  `_internal/resources/ffmpeg-9.0.1` in PyInstaller builds)

If you redistribute X-Track binaries that include FFmpeg:

1. Keep FFmpeg license/README files from the bundled folder.
2. Offer Corresponding Source for LGPL components as required by the LGPL
   (FFmpeg project source: https://github.com/FFmpeg/FFmpeg ).
3. Do not claim FFmpeg as your own product.

再分发含 FFmpeg 的二进制时，请保留捆绑目录中的许可文件，并按 LGPL
要求提供对应源码获取方式。

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
