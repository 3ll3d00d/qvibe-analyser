for %%f in (*.ui) do (
    C:\Users\mattk\dev\conda\envs\qvibe-analyser\Scripts\pyuic5.exe %%f -o "%%~nf.py"
)
