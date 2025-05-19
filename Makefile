ENV_NAME=chatbotEquirentV2

.PHONY: install update test-env clean help

install:
	@echo "🛠️ Creando entorno Conda '$(ENV_NAME)'..."
	bash scripts/setup_env.sh

update:
	@echo "🔄 Actualizando environment.yml desde el entorno '$(ENV_NAME)'..."
	conda run -n $(ENV_NAME) bash scripts/update_deps.sh

test-env:
	@echo "✅ Verificando si el entorno '$(ENV_NAME)' existe..."
	bash scripts/test_env.sh

clean:
	@echo "🧹 Eliminando entorno Conda '$(ENV_NAME)'..."
	conda env remove --name $(ENV_NAME)

help:
	@echo "Comandos disponibles:"
	@echo "  make install     - Crea el entorno Conda desde environment.yml"
	@echo "  make update      - Exporta y actualiza environment.yml con nuevas dependencias"
	@echo "  make test-env    - Verifica si el entorno existe"
	@echo "  make clean       - Elimina el entorno Conda"
