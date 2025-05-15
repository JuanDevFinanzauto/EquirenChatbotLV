ENV_NAME="chatbotEquirentV2"

if conda info --envs | grep "$ENV_NAME"; then
  echo "✅ El entorno '$ENV_NAME' existe."
else
  echo "❌ El entorno '$ENV_NAME' no existe."
fi