#!/bin/bash
clear
set -e  # Exit on anyt error

LOGFILE="setup.log"

trap 'cleanup' INT TERM ERR

cleanup() {
  echo -e "\n🛑 Script interrupted. Performing cleanup..."

  if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
  fi

  if [[ -d "anythingllm" ]]; then
    rm -rf anythingllm
    echo "🧹 Removed incomplete anythingllm directory"
  fi

  rm -f setup.log
  echo "🧹 Removed log file"

  echo "🧼 Cleanup complete. You can rerun the script safely."
  exit 1
}

exec > >(tee -a "$LOGFILE") 2>&1

# --- RedactAI Setup Script (macOS + Raspberry Pi Compatible) ---

if [[ "$1" == "--dev" ]]; then
  echo "🛠  Development mode enabled: skipping hardware check."
else
  ARCH=$(uname -m)
  if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This setup script is intended for Raspberry Pi (ARM) or macOS systems."
    echo "💡 Run with --dev to override: ./setup.sh --dev"
    exit 1
  fi
fi

echo -e "\n🔧 Starting RedactAI setup (macOS or Raspberry Pi)..."

if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "🍎 Detected macOS — installing dependencies..."
  which -s brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" &> /dev/null
  brew install node python3 git &> /dev/null
  brew link --overwrite node &> /dev/null || true
else
  echo "🐧 Detected Linux — installing dependencies..."
  sudo apt update -y &> /dev/null
  sudo apt upgrade -y &> /dev/null
  sudo apt install -y git nodejs npm python3-pip python3-venv build-essential curl &> /dev/null
fi

VALID_MODELS=("gpt-4o" "gpt-4" "gpt-3.5-turbo" "claude-3-opus-20240229" "claude-3-haiku" "gemini-pro" "gemini-1.5-pro")

echo -e "\n💡 Supported LLMs and where to find model names:"
echo "   🔹 OpenAI (ChatGPT): https://platform.openai.com/docs/models"
echo "   🔹 Azure OpenAI: https://learn.microsoft.com/en-us/azure/cognitive-services/openai/concepts/models"
echo "   🔹 Claude: https://docs.anthropic.com/claude/docs/models-overview"
echo "   🔹 Gemini: https://ai.google.dev/models/gemini\n"

echo -e "\n🧠 Choose your preferred model:"
PS3="Select model number (or type 0 to enter custom model): "
select MODEL_NAME in "${VALID_MODELS[@]}"; do
  if [[ -n "$MODEL_NAME" ]]; then
    break
  elif [[ "$REPLY" == "0" ]]; then
    read -p "🔧 Enter your custom model name: " MODEL_NAME
    break
  else
    echo "❌ Invalid selection. Try again."
  fi
done

API_URL_OPTIONS=(
  "https://api.openai.com/v1"
  "https://api.anthropic.com"
  "https://generativelanguage.googleapis.com/v1beta"
  "Custom URL"
)

echo -e "\n🌐 Select your API base URL:"
PS3="Select API base URL (or type 4 for custom): "
select API_BASE_URL in "${API_URL_OPTIONS[@]}"; do
  if [[ "$API_BASE_URL" == "Custom URL" ]]; then
    read -p "🔧 Enter your custom API base URL: " API_BASE_URL
    break
  elif [[ -n "$API_BASE_URL" ]]; then
    break
  else
    echo "❌ Invalid selection. Try again."
  fi
done

read -p "🔐 API Key: " API_KEY

echo -e "\n📁 Creating base project files..."
touch README.md LICENSE .gitignore

cat <<EOF > .gitignore
__pycache__/
.venv/
.env
*.log
*.pyc
*.swp
.DS_Store
EOF

cat <<EOF > README.md
# RedactAI

A local AI agent that redacts sensitive content from uploaded documents before securely sending them to a user-defined cloud LLM (e.g. GPT-4o) for further processing. Compatible with Raspberry Pi and macOS. Built on AnythingLLM.
EOF

cat <<EOF > LICENSE
MIT License

Copyright (c) $(date +%Y) YourName

Permission is hereby granted, free of charge, to any person obtaining a copy...
EOF

echo -e "\n🐍 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip &> /dev/null

if [ ! -f requirements.txt ]; then
  echo -e "📄 Generating requirements.txt..."
  cat <<EOF > requirements.txt
pdfminer.six==20250506
PyMuPDF==1.26.0
python-docx==1.1.0
cryptography==45.0.3
cffi==1.17.1
pycparser==2.22
charset-normalizer==3.4.2
EOF
fi

pip install -r requirements.txt &> /dev/null || { echo "❌ Python package install failed"; exit 1; }

if [ ! -d "anythingllm/.git" ]; then
  echo -e "\n📥 Cloning AnythingLLM..."
  mkdir -p anythingllm
  cd anythingllm
  git clone https://github.com/Mintplex-Labs/anything-llm.git . &> /dev/null || { echo "❌ Clone failed"; exit 1; }
  cd ..
else
  echo -e "\n📁 AnythingLLM already exists — skipping clone."
fi

echo -e "\n📦 Installing Yarn and project dependencies..."
npm install -g yarn &> /dev/null
cd anythingllm
npm install --force &> /dev/null || { echo "❌ npm install failed"; exit 1; }

echo -e "\n⚙️ Running AnythingLLM setup..."
npm run setup &> /dev/null || { echo "❌ AnythingLLM setup failed"; exit 1; }

cat <<EOF > server/.env.development
OPENAI_API_KEY=${API_KEY}
OPENAI_BASE_URL=${API_BASE_URL}
DEFAULT_OPENAI_MODEL=${MODEL_NAME}
EOF

cat <<EOF > frontend/.env
VITE_OPENAI_API_KEY=${API_KEY}
VITE_OPENAI_BASE_URL=${API_BASE_URL}
VITE_DEFAULT_OPENAI_MODEL=${MODEL_NAME}
EOF

cat <<EOF > collector/.env
OPENAI_API_KEY=${API_KEY}
OPENAI_BASE_URL=${API_BASE_URL}
DEFAULT_OPENAI_MODEL=${MODEL_NAME}
EOF

cd ..

trap - INT TERM ERR

echo -e "\n✅ RedactAI setup complete."
echo -e "\n👉 To launch the agent, run this in your terminal:"
echo "   cd anythingllm && npm run dev:all"
echo -e "\n🌐 Then access the UI at: http://localhost:3001"
echo -e "📁 Upload documents via the UI — redaction will be applied before LLM processing."
echo -e "🔐 Only redacted content is ever sent to the cloud."
