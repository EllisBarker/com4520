# com4520-darwin

## Setup

1. Clone the repository
2. Change directory to the repository
3. Install Graphviz:
    ```bash
    sudo apt-get install python3-dev graphviz libgraphviz-dev pkg-config
    ```
4. Create a virtual environment and setup dependencies:
    ```bash
    python -m venv ~/.venv/darwin
    ```
    ```bash
    source ~/.venv/darwin/bin/activate
    ```
    ```bash
    pip install -r requirements.txt
    ```

## Running Experiments
Either:
```bash
python experiments.py
```
or:
```bash
mpiexec -n 4 python hpc_experiments.py
```
