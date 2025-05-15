ENV_NAME="chatbotEquirentV2"
ENV_FILE="environment.yml"

echo "Creando entorno Conda '$ENV_NAME' desde $ENV_FILE..."
conda env create -f $ENV_FILE --name $ENV_NAME
echo "Entorno creado con éxito."