set -ex
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
poetry install

# python -m venv .
# pip install -r requirements.txt
# echo "ready. run:"
# echo "  source Scripts/activate"
# echo "in this folder before running druid when you've opened a new shell"
