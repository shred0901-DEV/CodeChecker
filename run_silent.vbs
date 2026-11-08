' CodeChecker Silent Launcher
' コマンドプロンプトの黒い画面を表示せずにアプリを起動します
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c run.bat", 0, False

