#!/bin/bash

# Wait for Ollama server to be available
echo "Waiting for Ollama server..."
until curl -s http://llm-server:11434/api/tags > /dev/null; do
    sleep 5
done

# Check if the model is already pulled
if ! curl -s http://llm-server:11434/api/tags | grep -q "\"${LLM_MODEL}\""; then
    echo "Pulling ${LLM_MODEL} model..."
    curl -X POST http://llm-server:11434/api/pull -d "{\"model\": \"${LLM_MODEL}\"}"
else
    echo "${LLM_MODEL} model already pulled"
fi

echo "LLM setup complete"
