@echo off
set PYTHONIOENCODING=utf-8
echo Running all tests...
python -m unittest discover -s src/workflow_module/actions/tests -p "test_step_*.py"
pause
