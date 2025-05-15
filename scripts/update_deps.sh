ENV_NAME="chatbotEquirentV2"
EXPORT_FILE="environment.yml"

echo "Activando entorno $ENV_NAME..."
conda activate $ENV_NAME

echo "Exportando dependencias instaladas manualmente a $EXPORT_FILE..."
conda env export --from-history > $EXPORT_FILE

echo "Archivo de entorno actualizado."