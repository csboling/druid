set -ex
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
poetry install
set +x
echo "see you back here after you've added poetry to your path and restarted your shell"
echo "then: poetry run python druid.py"
