for %%f in (*.ui) do (
    C:\Users\mattk\Anaconda3_64\envs\qvibe-analyser\Scripts\pyuic5.exe %%f -o "%%~nf.py"
)
