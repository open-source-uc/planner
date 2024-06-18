# This is the [INFO] prefix in bold cyan
info_prefix := `echo "\e[1;36m[Info]\e[0m"`
set dotenv-load := true

default:
    @just --list

deps-front:
    @echo "{{ info_prefix }} \e[1mInstalling front-end dependencies...\e[0m"
    cd frontend && npm install

generate-client:
    @echo "{{ info_prefix }} \e[1mGenerating OpenAPI client...\e[0m"
    cd frontend && npm run generate

wait-backend-start:
    #!/usr/bin/env bash
    set -euo pipefail
    echo -e "{{ info_prefix }} \e[1mWaiting for back-end to start...\e[0m"
    # Activate poetry virtualenv
    source /workspaces/planner/backend/.venv/bin/activate
    cd frontend
    # Wait till localhost:8000 is available
    while ! http --check-status :8000/health 2> /dev/null; do
        sleep 1
    done
    echo -e "{{ info_prefix }} \e[1mBack-end started.\e[0m"

generate-client-watch: wait-backend-start
    @echo "{{ info_prefix }} \e[1mStarting watcher to generate OpenAPI client when needed...\e[0m"
    # Use nodemon to track changes
    cd frontend && npx --yes nodemon -e py --watch ../backend/ --exec "npm run generate" --signal SIGTERM

generate-client-on-start: wait-backend-start generate-client
    
deps-back:
    @echo "{{ info_prefix }} \e[1mInstalling back-end dependencies...\e[0m"
    cd backend && poetry config virtualenvs.in-project true
    cd backend && poetry install

deps-infra:
    @echo "{{ info_prefix }} \e[1mInstalling infrastructure dependencies...\e[0m"
    cd backend && poetry run ansible-galaxy install -r ../infra/requirements.yml

deps: deps-front deps-back deps-infra

lint-front:
    @echo "{{ info_prefix }} \e[1mLinting front-end...\e[0m"
    cd frontend && npm run lint

lint-back:
    @echo "{{ info_prefix }} \e[1mLinting back-end...\e[0m"
    cd backend && poetry run ruff format --diff .
    cd backend && poetry run ruff check .
    cd backend && poetry run pyright

lint: lint-front lint-back

format-front:
    @echo "{{ info_prefix }} \e[1mFormatting front-end...\e[0m"
    cd frontend && npm run format

format-back:
    @echo "{{ info_prefix }} \e[1mFormatting back-end...\e[0m"
    cd backend && poetry run ruff format .

format: format-front format-back

lint-fix-front:
    @echo "{{ info_prefix }} \e[1mChecking & fixing front-end...\e[0m"
    cd frontend && npm run lint:fix
    cd frontend && npm run type-check

lint-fix-back:
    @echo "{{ info_prefix }} \e[1mChecking & fixing back-end...\e[0m"
    cd backend && poetry run ruff format .
    cd backend && poetry run ruff check . --fix
    cd backend && poetry run pyright
    cd backend && poetry run pytest

lint-fix: lint-fix-back lint-fix-front

init: deps
    @echo "{{ info_prefix }} \e[1mInitializing developer environment...\e[0m"
    @echo "{{ info_prefix }} \e[1mCreating default files...\e[0m"
    cd backend && cp -n .env.development.template .env
    cd frontend && cp -n .env.development.template .env
    cd cas-mock/data && cp -n cas-mock-users.json.example cas-mock-users.json
    @echo "{{ info_prefix }} \e[1mSetting up database...\e[0m"
    @just db-reset
    @echo "{{ info_prefix }} \e[1mInitialized developer environment successfully 🚀.\e[0m"

db-studio:
    @echo "{{ info_prefix }} \e[1mStarting Prisma Studio...\e[0m"
    cd backend && poetry run prisma studio

db-migrate:
    @echo "{{ info_prefix }} \e[1mRunning and generating database migrations...\e[0m"
    cd backend && poetry run prisma migrate dev

db-reset:
    @echo "{{ info_prefix }} \e[1mResetting and initializing database...\e[0m"
    cd backend && poetry run prisma migrate reset --force

db-generate:
    @echo "{{ info_prefix }} \e[1mGenerating Prisma client...\e[0m"
    cd backend && poetry run prisma generate

run:
    @echo "{{ info_prefix }} \e[1mRunning backend + frontend + CAS mock\e[0m"
    (npx --yes cas-server-mock --database=$PWD/cas-mock/data/cas-mock-users.json) & (cd frontend && npm run dev) & (cd backend && poetry run uvicorn app.main:app) && fg

set positional-arguments := true
default_environment := "development"
deploy environment=default_environment:
    #!/usr/bin/env bash
    set -eEuo pipefail
    DEPLOY_ENVIRONMENT={{ environment }}
    # If DEPLOY_ENVIRONMENT is not development, staging or production, exit
    if [[ "$DEPLOY_ENVIRONMENT" != "development" && "$DEPLOY_ENVIRONMENT" != "staging" && "$DEPLOY_ENVIRONMENT" != "production" ]]; then
        echo "Invalid deployment target: $DEPLOY_ENVIRONMENT"
        exit 1
    fi
    echo -e "{{ info_prefix }} \e[1mDeploying to $DEPLOY_ENVIRONMENT...\e[0m"
    # If deploy is not development, fetch code first
    if [[ "$DEPLOY_ENVIRONMENT" != "development" ]]; then
        echo -e "{{ info_prefix }} \e[1mFetching code from main...\e[0m"
        git config advice.detachedHead false
        git fetch --all
        git checkout --force origin/main
    fi
    echo -e "{{ info_prefix }} \e[1mBuilding containers...\e[0m"
    docker compose build --pull --build-arg DEPLOY_ENVIRONMENT=$DEPLOY_ENVIRONMENT
    # If DEPLOY_ENVIRONMENT is development, then we need to
    # also deploy the CAS mock service
    # Define target service
    if [[ "$DEPLOY_ENVIRONMENT" == "development" ]]; then
        TARGET_SERVICE=""
    else
        TARGET_SERVICE="planner"
    fi
    echo -e "{{ info_prefix }} \e[1mStarting containers...\e[0m"
    docker compose up --build --remove-orphans --force-recreate --detach --wait-timeout 300 --wait $TARGET_SERVICE
    echo -e "{{ info_prefix }} \e[1mDeployed to $DEPLOY_ENVIRONMENT successfully 🚀.\e[0m"