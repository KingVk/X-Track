# Optional local FFmpeg for development only.
# Release builds do NOT ship these binaries (GitHub 100MB limit + smaller zips).
#
# Runtime resolution order:
#   1) %USERPROFILE%\.xtrack\bin\ffmpeg.exe  (in-app download / manual)
#   2) ffmpeg on PATH (winget / chocolatey / system)
#   3) this folder (dev convenience)
#
# Place ffmpeg.exe / ffprobe.exe here if you want a project-local copy while coding.
