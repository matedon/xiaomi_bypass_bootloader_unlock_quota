@echo off
setlocal enabledelayedexpansion

rem Liste des hôtes à tester
set hosts=ntp.tencent.com cn.pool.ntp.org edu.ntp.org.cn time.apple.com time.google.com pool.ntp.org 161.117.96.161 20.157.18.26

for %%h in (%hosts%) do (
    echo Test de %%h
    ping %%h -n 4
    echo ---------------------------
)

endlocal
pause

