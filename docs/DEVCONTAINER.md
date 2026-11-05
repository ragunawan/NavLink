# Develop in a container

The devcontainer provides the same Linux environment on Windows, macOS and Linux, with Python 3.12, Node 22, npm, Git, Make, SQLite with FTS5, and Chromium for Playwright. Python and Node match the versions used in CI. Creating or rebuilding the devcontainer needs internet access for the image, development tools, dependencies and Chromium.

## Open the project

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux), [VS Code](https://code.visualstudio.com/), and the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. On Windows, enable Docker Desktop's **WSL 2 backend** and use **Linux containers**. For faster file access, clone the repository into your WSL Linux filesystem (for example, `~/src/navylink`) and open it from WSL with `code .`. Enable Docker Desktop's integration for that WSL distribution. A Windows filesystem checkout also works; polling is enabled for frontend and backend reloads. See Microsoft's [Windows and volume guidance](https://code.visualstudio.com/remote/advancedcontainers/improve-performance).
3. Open the repository folder in VS Code, run **Dev Containers: Reopen in Container** from the Command Palette, and wait for setup to finish. You can also use **Dev Containers: Clone Repository in Container Volume...** to keep the entire checkout in Docker storage.

Setup creates `.env` from `.env.example` if needed, installs dependencies, initializes an empty development database with the fictional regression fixtures, builds the frontend, and installs Chromium and its Linux dependencies. Existing `.env` settings are preserved. The default configuration needs no model download or API key. For the optional neural encoder, leave `NAVYLINK_MODEL_PATH` unset during initial setup, then run `make model` before enabling that setting and running `make reindex` as described in the [README](../README.md#search-and-overlap-decisions).

The commands below run in VS Code's **container terminal**. Python, Node and Make do not need to be installed on the host.

## Run and verify

For the compiled app:

```sh
make run
```

Open http://127.0.0.1:8000; API documentation is at http://127.0.0.1:8000/docs.

For live frontend and backend reloads, run these in separate terminals:

```sh
make dev-api
```

```sh
make dev-ui
```

Open http://127.0.0.1:5173. VS Code forwards ports 8000, 5173 and 8013; the servers can retain their loopback bindings. If a host port is already in use, use the local address shown in VS Code's **Ports** tab.

```sh
make test      # backend tests, TypeScript checks and frontend build
make evaluate  # writes docs/evaluation.json using a temporary database
```

For browser tests, start a separate API with a fresh temporary regression database:

```sh
NAVYLINK_DB="$(mktemp -d)/navylink.db" .venv/bin/python -m uvicorn navylink.main:app --host 127.0.0.1 --port 8013
```

Then, in another terminal:

```sh
NAVYLINK_TEST_URL=http://127.0.0.1:8013 npm --prefix frontend test
```

To use the 500-project sample catalog, stop the development server and run `make sample`, then restart it. This backs up and replaces the container's catalog. See the [sample import instructions](data/README.md#sample-catalog).

## Dependencies and saved data

The source tree is shared with the host. Separate Docker named volumes hold `.venv`, `frontend/node_modules`, and `/var/lib/navylink` so dependencies built for Windows or macOS cannot interfere with the Linux environment. The volumes are unique to this devcontainer and persist across container rebuilds.

Inside the container, `NAVYLINK_DB` is set to `/var/lib/navylink/navylink.db`. This environment variable takes precedence over the value in `.env`; the host's `data/navylink.db` and the deployment Compose volume are separate. SQLite backups from `make sample` also stay in the development data volume. Removing that volume deletes its database and backups. Changes to tracked source files, including evaluation results and screenshots, are still visible on the host.

After changing requirements or the npm lockfile, run `make setup`. After changing Playwright, also run `cd frontend && npx playwright install --with-deps chromium`. After changing `devcontainer.json`, run **Dev Containers: Rebuild Container**; setup runs again and keeps existing catalog data. To recover from a failed initial download, rerun `bash .devcontainer/post-create.sh` inside the container.

Git uses LF line endings for text files through `.gitattributes`. If an older Windows checkout still has CRLF endings in `.devcontainer/post-create.sh`, select **LF** in VS Code's status bar and save it before reopening the container.

The root `Dockerfile` and `compose.yaml` remain the deployment and offline packaging workflow described in the [README](../README.md#offline-packaging).
