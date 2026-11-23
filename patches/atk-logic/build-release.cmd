@echo off
rem Rebuild ATK-Logic (Release x64) from this work dir. Deps (Qt, vcpkg glib/libusb, Python NuGet, jom) must already be present.
setlocal
set "WD=%~dp0"
set "WD=%WD:~0,-1%"
set "TEMP=%WD%\tmp" & set "TMP=%WD%\tmp"
set "CMAKE=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1

rem 1. atk_libsigrokdecode (static) + irmp.dll
"%CMAKE%" -S "%WD%\srd-msvc" -B "%WD%\build-srd" -G Ninja -DCMAKE_BUILD_TYPE=Release "-DVCPKG_INSTALLED=%WD%/vcpkg/installed/x64-windows-rel" "-DPYTHON_ROOT=%WD%/python-nuget/tools" || exit /b 1
"%CMAKE%" --build "%WD%\build-srd" || exit /b 1
copy /y "%WD%\build-srd\atk_decoder.lib" "%WD%\deps\lib\" >nul

rem 2. App, Release only (never build the Debug configuration)
if not exist "%WD%\build-app" mkdir "%WD%\build-app"
pushd "%WD%\build-app"
"%WD%\Qt\5.15.2\msvc2019_64\bin\qmake.exe" "%WD%\src\ATK-Logic.pro" -spec win32-msvc "CONFIG+=release" "ATK_DEPS_DIR=%WD%/deps" || exit /b 1
"%WD%\jom\jom.exe" /NOLOGO -f Makefile.Release || exit /b 1
popd
echo Built %WD%\build-app\release\ATK-Logic.exe  (re-run the dist/windeployqt + DLL copy steps to refresh dist\ATK-Logic)
